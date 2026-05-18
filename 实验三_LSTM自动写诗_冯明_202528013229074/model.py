from __future__ import annotations

import torch
from torch import nn


class PoetryLSTM(nn.Module):
    """基于双层 LSTM 的唐诗语言模型（自己设计方案）。

    【与实验指导书示例的区别】
    指导书示例：Embedding -> 单层 LSTM -> Linear（无 Dropout）
    本方案改进：
      1. 使用 2 层 LSTM（num_layers=2），增强模型对长程诗句依赖的建模能力
      2. 在 LSTM 输出后增加独立 Dropout 层（dropout=0.3），缓解过拟合
      3. 生成脚本使用 temperature + top-k 采样，相比贪心解码生成更有韵律变化

    输入: (B, seq_len) 整数 token id
    输出: logits (B, seq_len, vocab_size) + hidden state
    """

    def __init__(
        self,
        vocab_size: int,
        embed_dim: int = 256,      # 字符嵌入维度
        hidden_dim: int = 512,     # LSTM 隐状态维度
        num_layers: int = 2,       # LSTM 层数（自己方案：2层）
        dropout: float = 0.3,      # Dropout 比例
        pad_idx: int = 0,          # padding token 的 id，不参与梯度计算
    ) -> None:
        super().__init__()
        # 字符嵌入层，pad_idx 对应的向量梯度置零
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=pad_idx)
        # 双层 LSTM；num_layers>1 时层间自动加 Dropout（最后一层不加）
        self.lstm = nn.LSTM(
            embed_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        # LSTM 输出后的额外 Dropout（指导书示例无此层）
        self.dropout = nn.Dropout(dropout)
        # 线性层将隐状态映射到词表 logits
        self.fc = nn.Linear(hidden_dim, vocab_size)

    def forward(
        self, x: torch.Tensor, hidden: tuple[torch.Tensor, torch.Tensor] | None = None
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        # x: (B, seq_len) -> emb: (B, seq_len, embed_dim)
        emb = self.embedding(x)
        # out: (B, seq_len, hidden_dim)；hidden 传递隐状态用于生成时的逐步前向
        out, hidden = self.lstm(emb, hidden)
        out = self.dropout(out)                 # 防止过拟合
        logits = self.fc(out)                   # (B, seq_len, vocab_size)
        return logits, hidden
