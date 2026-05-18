from __future__ import annotations

import math

import torch
from torch import nn


class PatchEmbedding(nn.Module):
    """将图像切分为固定大小的 Patch 并映射到 embed_dim 维向量。

    使用 stride=patch_size 的卷积实现非重叠 Patch 分割，等价于
    将每个 patch 展平后过一个线性层，但卷积实现更高效。
    输入: (B, C, H, W) -> 输出: (B, num_patches, embed_dim)
    """

    def __init__(self, in_chans: int, embed_dim: int, patch_size: int) -> None:
        super().__init__()
        # 卷积核大小 = stride = patch_size，保证 patch 不重叠
        self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.proj(x)               # (B, embed_dim, H/p, W/p)
        x = x.flatten(2).transpose(1, 2)  # (B, num_patches, embed_dim)
        return x


class MLP(nn.Module):
    """Transformer Block 中的前馈网络（FFN）。

    结构：Linear -> GELU -> Dropout -> Linear -> Dropout
    hidden_dim 通常为 embed_dim 的 4 倍（mlp_ratio=4.0）。
    """

    def __init__(self, dim: int, hidden_dim: int, dropout: float) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.GELU(),          # ViT 原文使用 GELU 激活
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class TransformerBlock(nn.Module):
    """标准 ViT Transformer 编码器块。

    结构（Pre-Norm 形式）：
      x = x + MultiHeadAttention(LayerNorm(x))
      x = x + FFN(LayerNorm(x))
    Pre-Norm 比 Post-Norm 训练更稳定，是 ViT 的标准做法。
    """

    def __init__(self, dim: int, num_heads: int, mlp_ratio: float, dropout: float) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        # PyTorch 内置多头自注意力；batch_first=True 使输入格式为 (B, N, D)
        self.attn = nn.MultiheadAttention(dim, num_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(dim)
        self.mlp = MLP(dim, int(dim * mlp_ratio), dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 残差连接 + 多头自注意力（Pre-Norm）
        attn_out, _ = self.attn(self.norm1(x), self.norm1(x), self.norm1(x), need_weights=False)
        x = x + attn_out
        # 残差连接 + 前馈网络（Pre-Norm）
        x = x + self.mlp(self.norm2(x))
        return x


class VisionTransformer(nn.Module):
    """从零实现的 Vision Transformer（ViT），用于 CIFAR10 分类。

    针对 CIFAR10（32×32）的适配：
    - patch_size=4（原文针对 224×224 用 16），使 num_patches=64
    - embed_dim=192，depth=6，num_heads=3（轻量配置，适合从零训练）
    - 分类使用 CLS token，与原始 ViT 论文一致

    参考：Dosovitskiy et al., "An Image is Worth 16x16 Words", ICLR 2021
    """

    def __init__(
        self,
        image_size: int = 32,
        patch_size: int = 4,
        in_chans: int = 3,
        num_classes: int = 10,
        embed_dim: int = 192,
        depth: int = 6,
        num_heads: int = 3,
        mlp_ratio: float = 4.0,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        assert image_size % patch_size == 0, "image_size must be divisible by patch_size"
        self.num_patches = (image_size // patch_size) ** 2  # CIFAR10: (32/4)^2 = 64
        # Patch 嵌入层：将图像分块并线性投影
        self.patch_embed = PatchEmbedding(in_chans, embed_dim, patch_size)
        # 可学习的分类 token，拼接到 patch 序列最前面
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        # 可学习的位置编码（长度 = num_patches + 1，含 cls_token）
        self.pos_embed = nn.Parameter(torch.zeros(1, self.num_patches + 1, embed_dim))
        self.pos_drop = nn.Dropout(dropout)
        # 堆叠 depth 个 Transformer Block
        self.blocks = nn.Sequential(
            *[TransformerBlock(embed_dim, num_heads, mlp_ratio, dropout) for _ in range(depth)]
        )
        self.norm = nn.LayerNorm(embed_dim)   # 最终 LayerNorm
        self.head = nn.Linear(embed_dim, num_classes)  # 分类头
        self._init_weights()

    def _init_weights(self) -> None:
        # 截断正态初始化，标准差 0.02 为 ViT 原文推荐值
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
        nn.init.trunc_normal_(self.cls_token, std=0.02)
        nn.init.trunc_normal_(self.head.weight, std=0.02)
        nn.init.zeros_(self.head.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.patch_embed(x)                          # (B, 64, 192)
        # 将 cls_token 扩展到 batch 维度并拼接到序列头部
        cls_tokens = self.cls_token.expand(x.size(0), -1, -1)  # (B, 1, 192)
        x = torch.cat((cls_tokens, x), dim=1)            # (B, 65, 192)
        x = x + self.pos_embed[:, : x.size(1)]           # 加位置编码
        x = self.pos_drop(x)
        x = self.blocks(x)                               # 经过所有 Transformer Block
        x = self.norm(x)
        return self.head(x[:, 0])                        # 取 cls_token 位置输出分类
