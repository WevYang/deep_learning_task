from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Subset, random_split
from torchvision import datasets, transforms

from core import download_file, ensure_dir, extract_archive

try:
    from datasets import load_dataset
except ImportError:  # pragma: no cover - optional dependency
    load_dataset = None


CIFAR10_URL = "https://data.brainchip.com/dataset-mirror/cifar10/cifar-10-python.tar.gz"


@dataclass
class CIFAR10Data:
    train_loader: DataLoader
    val_loader: DataLoader
    test_loader: DataLoader


class _HFCifar10Dataset(torch.utils.data.Dataset):
    def __init__(self, dataset, transform=None):
        self.dataset = dataset
        self.transform = transform

    def __len__(self) -> int:
        return len(self.dataset)

    def __getitem__(self, idx: int):
        row = self.dataset[int(idx)]
        image = row["img"] if "img" in row else row["image"]
        label = int(row["label"])
        if self.transform is not None:
            image = self.transform(image)
        return image, label


def ensure_cifar10_dataset(data_dir: str | Path) -> Path:
    data_dir = ensure_dir(data_dir)
    if (data_dir / "cifar-10-batches-py").exists():
        return data_dir
    archive = data_dir / "cifar-10-python.tar.gz"
    try:
        download_file(CIFAR10_URL, archive, overwrite=True)
        extract_archive(archive, data_dir)
    except Exception:
        if archive.exists():
            part = archive.with_suffix(archive.suffix + ".part")
            if not part.exists():
                archive.rename(part)
            else:
                archive.unlink()
        download_file(CIFAR10_URL, archive, overwrite=True)
        extract_archive(archive, data_dir)
    if not (data_dir / "cifar-10-batches-py").exists():
        raise FileNotFoundError("Failed to extract CIFAR10 archive.")
    return data_dir


def build_cifar10_dataloaders(
    data_dir: str | Path,
    batch_size: int,
    val_ratio: float = 0.1,
    num_workers: int = 4,
    image_size: int = 32,
    max_train_samples: int | None = None,
    max_test_samples: int | None = None,
    source: str = "torchvision",
) -> CIFAR10Data:
    train_transform = transforms.Compose(
        [
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616)),
        ]
    )
    test_transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616)),
        ]
    )
    if source == "hf" and load_dataset is not None:
        hf = load_dataset("uoft-cs/cifar10")
        train_split = hf["train"]
        if max_train_samples is not None:
            train_split = train_split.select(range(min(max_train_samples, len(train_split))))
        if max_test_samples is not None:
            test_split = hf["test"].select(range(min(max_test_samples, len(hf["test"]))))
        else:
            test_split = hf["test"]
        train_split = train_split.train_test_split(test_size=val_ratio, seed=42)
        train_dataset = _HFCifar10Dataset(train_split["train"], transform=train_transform)
        val_dataset = _HFCifar10Dataset(train_split["test"], transform=test_transform)
        test_dataset = _HFCifar10Dataset(test_split, transform=test_transform)
    else:
        if source == "hf" and load_dataset is None:
            raise RuntimeError("datasets is not installed; use source='torchvision' or install datasets.")
        data_dir = Path(data_dir)
        ensure_cifar10_dataset(data_dir)
        train_base = datasets.CIFAR10(data_dir, train=True, download=False, transform=train_transform)
        val_base = datasets.CIFAR10(data_dir, train=True, download=False, transform=test_transform)
        if max_train_samples is not None:
            indices = list(range(min(max_train_samples, len(train_base))))
            train_base = Subset(train_base, indices)
            val_base = Subset(val_base, indices)
        permutation = torch.randperm(len(train_base), generator=torch.Generator().manual_seed(42)).tolist()
        if len(permutation) > 1:
            val_size = min(max(1, int(len(permutation) * val_ratio)), len(permutation) - 1)
        else:
            val_size = 0
        train_indices = permutation[val_size:]
        val_indices = permutation[:val_size]
        train_dataset = Subset(train_base, train_indices)
        val_dataset = Subset(val_base, val_indices)
        test_dataset = datasets.CIFAR10(data_dir, train=False, download=False, transform=test_transform)
        if max_test_samples is not None:
            test_dataset = Subset(test_dataset, list(range(min(max_test_samples, len(test_dataset)))))
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
    return CIFAR10Data(train_loader=train_loader, val_loader=val_loader, test_loader=test_loader)
