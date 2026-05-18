from __future__ import annotations

import torch
from torch import nn


class LeNetMNIST(nn.Module):
    """基于 LeNet 改进的 CNN，用于 MNIST 手写数字 10 分类。

    网络结构：两个卷积块（Conv-BN-ReLU-Conv-BN-ReLU-MaxPool-Dropout）
    后接全连接分类头，相比原始 LeNet 增加了 BatchNorm 和 Dropout 以提升泛化能力。
    """

    def __init__(self) -> None:
        super().__init__()
        # 特征提取部分：两个卷积块，每块包含两层卷积 + BN + ReLU + 池化 + Dropout
        self.features = nn.Sequential(
            # 第一卷积块：输入 (B,1,28,28) -> 输出 (B,32,14,14)
            nn.Conv2d(1, 32, kernel_size=3, padding=1),   # 保持空间尺寸不变
            nn.BatchNorm2d(32),                            # 批归一化，加速收敛
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                               # 下采样：28->14
            nn.Dropout2d(0.1),                             # 空间 Dropout，防止过拟合
            # 第二卷积块：输入 (B,32,14,14) -> 输出 (B,64,7,7)
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                               # 下采样：14->7
            nn.Dropout2d(0.2),
        )
        # 分类头：将展平后的特征映射到 10 个类别
        self.classifier = nn.Sequential(
            nn.Flatten(),                                  # (B,64,7,7) -> (B,3136)
            nn.Linear(64 * 7 * 7, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, 10),                            # 输出 10 类 logits
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        return self.classifier(x)
