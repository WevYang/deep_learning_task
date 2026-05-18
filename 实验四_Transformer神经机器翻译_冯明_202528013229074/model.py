from __future__ import annotations

import math

import torch
from torch import nn


class PositionalEncoding(nn.Module):
    """正弦余弦位置编码（Sinusoidal Positional Encoding）。

    来自 Vaswani et al. (2017) "Attention Is All You Need"：
      PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
      PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))

    相比可学习位置编码，正弦位置编码在推理时可外推到训练未见过的长度。
    位置编码与词嵌入相加，使模型同时感知 token 内容和序列位置。
    """

    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000) -> None:
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        # 预计算所有位置的编码矩阵，注册为 buffer（不参与梯度更新）
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        # 分母：10000^(2i/d_model)，用 exp(log) 形式保证数值稳定
        div_term = torch.exp(torch.arange(0, d_model, 2, dtype=torch.float) * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)  # 偶数维度用 sin
        pe[:, 1::2] = torch.cos(position * div_term)  # 奇数维度用 cos
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)，广播到 batch
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, seq_len, d_model)；截取对应长度的位置编码并相加
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


class TransformerNMT(nn.Module):
    """基于 Transformer Encoder-Decoder 的中英神经机器翻译模型。

    模型结构（遵循 Vaswani et al. 2017）：
      源端：中文 Embedding + 位置编码 -> Transformer Encoder（3层）
      目标端：英文 Embedding + 位置编码 -> Transformer Decoder（3层）
      生成头：Linear(d_model -> tgt_vocab_size) -> 逐位置预测目标词

    训练：使用 teacher forcing + causal mask（目标序列自回归掩码）
    推理：贪心解码或 beam search（beam_size=4，length_penalty α=0.7）
    """

    def __init__(
        self,
        src_vocab_size: int,
        tgt_vocab_size: int,
        d_model: int = 256,            # 模型隐层维度
        nhead: int = 4,                # 多头注意力头数
        num_encoder_layers: int = 3,   # Encoder 层数（简化自原文的 6 层）
        num_decoder_layers: int = 3,   # Decoder 层数
        dim_feedforward: int = 512,    # FFN 隐层维度（= 2 × d_model）
        dropout: float = 0.1,
        src_pad_idx: int = 0,          # 源端 padding token id
        tgt_pad_idx: int = 0,          # 目标端 padding token id
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.src_pad_idx = src_pad_idx
        self.tgt_pad_idx = tgt_pad_idx
        # 源/目标词嵌入（padding 位置梯度为零）
        self.src_embed = nn.Embedding(src_vocab_size, d_model, padding_idx=src_pad_idx)
        self.tgt_embed = nn.Embedding(tgt_vocab_size, d_model, padding_idx=tgt_pad_idx)
        # 共享同一个位置编码模块，源端和目标端均使用
        self.positional = PositionalEncoding(d_model, dropout)
        # PyTorch 内置 Transformer（batch_first=True 使输入为 (B, S, D)）
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        # 生成头：将 d_model 维隐状态映射到目标词表 logits
        self.generator = nn.Linear(d_model, tgt_vocab_size)

    def forward(
        self,
        src: torch.Tensor,                        # 源端 token ids (B, src_len)
        tgt_in: torch.Tensor,                     # 目标端输入（右移一位）(B, tgt_len)
        src_padding_mask: torch.Tensor | None = None,  # True 处为 padding
        tgt_padding_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        # 嵌入 + sqrt(d_model) 缩放（原文做法，防止嵌入值过小被位置编码淹没）+ 位置编码
        src_emb = self.positional(self.src_embed(src) * math.sqrt(self.d_model))
        tgt_emb = self.positional(self.tgt_embed(tgt_in) * math.sqrt(self.d_model))
        # 自回归掩码：防止 decoder 在训练时看到未来 token（上三角为 -inf）
        tgt_mask = nn.Transformer.generate_square_subsequent_mask(tgt_in.size(1)).to(src.device)
        out = self.transformer(
            src_emb,
            tgt_emb,
            tgt_mask=tgt_mask,
            src_key_padding_mask=src_padding_mask,
            tgt_key_padding_mask=tgt_padding_mask,
            memory_key_padding_mask=src_padding_mask,  # encoder 输出的 padding mask 也传给 decoder
        )
        return self.generator(out)  # (B, tgt_len, tgt_vocab_size)
