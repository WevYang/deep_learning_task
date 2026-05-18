from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import torch
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms


@dataclass
class MNISTData:
    train_loader: DataLoader
    val_loader: DataLoader
    test_loader: DataLoader


def build_mnist_dataloaders(
    data_dir: str | Path,
    batch_size: int,
    val_ratio: float = 0.1,
    num_workers: int = 4,
) -> MNISTData:
    data_dir = Path(data_dir)
    train_transform = transforms.Compose(
        [
            transforms.RandomAffine(degrees=10, translate=(0.05, 0.05), scale=(0.95, 1.05)),
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,)),
        ]
    )
    test_transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,)),
        ]
    )
    full_train = datasets.MNIST(data_dir, train=True, download=True, transform=train_transform)
    test_dataset = datasets.MNIST(data_dir, train=False, download=True, transform=test_transform)
    val_size = int(len(full_train) * val_ratio)
    train_size = len(full_train) - val_size
    train_dataset, val_dataset = random_split(
        full_train,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42),
    )
    val_dataset.dataset = datasets.MNIST(data_dir, train=True, download=True, transform=test_transform)  # type: ignore[attr-defined]
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )
    return MNISTData(train_loader=train_loader, val_loader=val_loader, test_loader=test_loader)

