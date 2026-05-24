"""Simple LeNet for MNIST — no BN so gradients are invertible for GRNN attack."""
import torch
import torch.nn as nn


class LeNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 6, 5, padding=2),   # 28x28 -> 28x28
            nn.ReLU(),
            nn.MaxPool2d(2),                  # 14x14
            nn.Conv2d(6, 16, 5),              # 10x10
            nn.ReLU(),
            nn.MaxPool2d(2),                  # 5x5
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(16 * 5 * 5, 120),
            nn.ReLU(),
            nn.Linear(120, 84),
            nn.ReLU(),
            nn.Linear(84, 10),
        )

    def forward(self, x):
        return self.classifier(self.features(x))
