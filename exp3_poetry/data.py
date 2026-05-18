from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, random_split

from core import ensure_dir, resolve_root


def _candidate_paths(data_dir: str | Path) -> list[Path]:
    data_dir = Path(data_dir)
    root = resolve_root()
    return [
        data_dir / "tang.npz",
        data_dir / "tang.npz.zip",
        root / "实验3" / "tang.npz",
        root / "实验3" / "tang.npz.zip",
        root / "实验3" / "tang.npz.zip.zip",
    ]


def ensure_tang_dataset(data_dir: str | Path) -> Path:
    data_dir = ensure_dir(data_dir)
    npz_path = data_dir / "tang.npz"
    if npz_path.exists():
        return npz_path
    for candidate in _candidate_paths(data_dir):
        if not candidate.exists():
            continue
        if candidate.suffix == ".npz":
            return candidate
        if candidate.suffix == ".zip":
            with zipfile.ZipFile(candidate) as zf:
                zf.extractall(data_dir)
            if npz_path.exists():
                return npz_path
    raise FileNotFoundError(
        "tang.npz not found. Place it in data_dir or keep the bundled archive under 实验3/."
    )


def load_tang_dataset(data_dir: str | Path) -> tuple[np.ndarray, dict[int, str], dict[str, int]]:
    npz_path = ensure_tang_dataset(data_dir)
    data = np.load(npz_path, allow_pickle=True)
    return data["data"], data["ix2word"].item(), data["word2ix"].item()


class PoetryDataset(Dataset):
    def __init__(self, data: np.ndarray) -> None:
        self.data = torch.from_numpy(data).long()

    def __len__(self) -> int:
        return self.data.size(0)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        seq = self.data[idx]
        return seq[:-1], seq[1:]


def build_poetry_loaders(
    data_dir: str | Path,
    batch_size: int,
    val_ratio: float = 0.05,
    num_workers: int = 4,
) -> tuple[DataLoader, DataLoader, dict[int, str], dict[str, int]]:
    data, ix2word, word2ix = load_tang_dataset(data_dir)
    dataset = PoetryDataset(data)
    val_size = max(1, int(len(dataset) * val_ratio))
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(
        dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42),
    )
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
    return train_loader, val_loader, ix2word, word2ix

