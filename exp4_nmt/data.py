from __future__ import annotations

import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import torch
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader, Dataset

from core import download_file, ensure_dir, extract_archive
from core.text import Vocab, tokenize_text


NIUTRANS_ZIP_URL = "https://github.com/NiuTrans/NiuTrans.SMT/archive/refs/heads/master.zip"
NIUTRANS_SAMPLE_TAR_URL = "https://raw.githubusercontent.com/NiuTrans/NiuTrans.SMT/master/sample-data/sample.tar.gz"
REQUIRED_FILES = [
    "train.zh",
    "train.en",
    "dev.zh",
    "dev.en",
    "test.zh",
    "test.en",
    "vocab.zh",
    "vocab.en",
]


def ensure_niutrans_dataset(data_dir: str | Path) -> Path:
    data_dir = ensure_dir(data_dir)
    if all((data_dir / name).exists() for name in REQUIRED_FILES):
        return data_dir

    sample_archive = data_dir / "sample.tar.gz"
    sample_root = ensure_dir(data_dir / "_sample_raw")
    try:
        download_file(NIUTRANS_SAMPLE_TAR_URL, sample_archive)
        extract_archive(sample_archive, sample_root)
        candidates = [p for p in sample_root.rglob("*") if p.is_dir()]
        candidates.insert(0, sample_root)
        for candidate in candidates:
            if all((candidate / name).exists() for name in REQUIRED_FILES):
                for name in REQUIRED_FILES:
                    shutil.copy2(candidate / name, data_dir / name)
                return data_dir
    except Exception:
        pass

    archive = data_dir / "NiuTrans.SMT.zip"
    extract_root = ensure_dir(data_dir / "_raw")
    try:
        download_file(NIUTRANS_ZIP_URL, archive)
        extract_archive(archive, extract_root)
    except Exception:
        if archive.exists():
            part = archive.with_suffix(archive.suffix + ".part")
            if not part.exists():
                archive.rename(part)
            else:
                archive.unlink()
        download_file(NIUTRANS_ZIP_URL, archive)
        extract_archive(archive, extract_root)

    sample_dirs = list(extract_root.rglob("sample-data"))
    if not sample_dirs:
        raise FileNotFoundError("sample-data directory was not found inside the NiuTrans archive.")
    sample_dir = sample_dirs[0]
    for name in REQUIRED_FILES:
        src = sample_dir / name
        if not src.exists():
            continue
        shutil.copy2(src, data_dir / name)
    if not all((data_dir / name).exists() for name in REQUIRED_FILES):
        raise FileNotFoundError("Failed to prepare the full NiuTrans sample dataset.")
    return data_dir


def _read_lines(path: Path, lowercase: bool = False) -> list[list[str]]:
    lines: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        tokens = line.strip().split()
        if lowercase:
            tokens = [tok.lower() for tok in tokens]
        if tokens:
            lines.append(tokens)
    return lines


def load_vocab(path: Path, specials: Sequence[str]) -> Vocab:
    tokens: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        token = parts[0]
        if token not in tokens:
            tokens.append(token)
    itos = list(dict.fromkeys(list(specials) + tokens))
    stoi = {tok: i for i, tok in enumerate(itos)}
    return Vocab(
        stoi=stoi,
        itos=itos,
        pad_token=specials[0],
        unk_token=specials[1],
        bos_token=specials[2],
        eos_token=specials[3],
    )


def build_vocab_from_data(lines: list[list[str]], specials: Sequence[str]) -> Vocab:
    counter = Counter(token for sent in lines for token in sent)
    itos = list(dict.fromkeys(list(specials)))
    for token, _ in counter.most_common():
        if token not in itos:
            itos.append(token)
    stoi = {tok: i for i, tok in enumerate(itos)}
    return Vocab(
        stoi=stoi,
        itos=itos,
        pad_token=specials[0],
        unk_token=specials[1],
        bos_token=specials[2],
        eos_token=specials[3],
    )


@dataclass
class ParallelExample:
    src: list[int]
    tgt_in: list[int]
    tgt_out: list[int]


class TranslationDataset(Dataset):
    def __init__(
        self,
        src_sentences: list[list[str]],
        tgt_sentences: list[list[str]],
        src_vocab: Vocab,
        tgt_vocab: Vocab,
        max_length: int = 80,
    ) -> None:
        self.examples: list[ParallelExample] = []
        for src_tokens, tgt_tokens in zip(src_sentences, tgt_sentences):
            src_tokens = src_tokens[: max_length - 2]
            tgt_tokens = tgt_tokens[: max_length - 2]
            src_ids = [src_vocab.bos_idx] + src_vocab.encode(src_tokens) + [src_vocab.eos_idx]
            tgt_in = [tgt_vocab.bos_idx] + tgt_vocab.encode(tgt_tokens)
            tgt_out = tgt_vocab.encode(tgt_tokens) + [tgt_vocab.eos_idx]
            if len(src_ids) <= max_length and len(tgt_in) <= max_length and len(tgt_out) <= max_length:
                self.examples.append(ParallelExample(src_ids, tgt_in, tgt_out))

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> ParallelExample:
        return self.examples[idx]


def collate_translation_batch(batch: Sequence[ParallelExample], src_pad_idx: int, tgt_pad_idx: int):
    src = [torch.tensor(example.src, dtype=torch.long) for example in batch]
    tgt_in = [torch.tensor(example.tgt_in, dtype=torch.long) for example in batch]
    tgt_out = [torch.tensor(example.tgt_out, dtype=torch.long) for example in batch]
    src_padded = pad_sequence(src, batch_first=True, padding_value=src_pad_idx)
    tgt_in_padded = pad_sequence(tgt_in, batch_first=True, padding_value=tgt_pad_idx)
    tgt_out_padded = pad_sequence(tgt_out, batch_first=True, padding_value=tgt_pad_idx)
    src_padding_mask = src_padded.eq(src_pad_idx)
    tgt_padding_mask = tgt_in_padded.eq(tgt_pad_idx)
    return src_padded, tgt_in_padded, tgt_out_padded, src_padding_mask, tgt_padding_mask


@dataclass
class NMTData:
    train_loader: DataLoader
    dev_loader: DataLoader
    test_loader: DataLoader
    src_vocab: Vocab
    tgt_vocab: Vocab


def build_nmt_dataloaders(
    data_dir: str | Path,
    batch_size: int,
    max_length: int = 80,
    num_workers: int = 4,
    max_train_samples: int | None = None,
    max_dev_samples: int | None = None,
    max_test_samples: int | None = None,
) -> NMTData:
    root = ensure_niutrans_dataset(data_dir)
    src_specials = ["<pad>", "<unk>", "<s>", "</s>"]
    tgt_specials = ["<pad>", "<unk>", "<s>", "</s>"]
    src_vocab = load_vocab(root / "vocab.zh", src_specials)
    tgt_vocab = load_vocab(root / "vocab.en", tgt_specials)

    train_src = _read_lines(root / "train.zh")
    train_tgt = _read_lines(root / "train.en", lowercase=True)
    dev_src = _read_lines(root / "dev.zh")
    dev_tgt = _read_lines(root / "dev.en", lowercase=True)
    test_src = _read_lines(root / "test.zh")
    test_tgt = _read_lines(root / "test.en", lowercase=True)

    if max_train_samples is not None:
        train_src = train_src[:max_train_samples]
        train_tgt = train_tgt[:max_train_samples]
    if max_dev_samples is not None:
        dev_src = dev_src[:max_dev_samples]
        dev_tgt = dev_tgt[:max_dev_samples]
    if max_test_samples is not None:
        test_src = test_src[:max_test_samples]
        test_tgt = test_tgt[:max_test_samples]

    train_dataset = TranslationDataset(train_src, train_tgt, src_vocab, tgt_vocab, max_length=max_length)
    dev_dataset = TranslationDataset(dev_src, dev_tgt, src_vocab, tgt_vocab, max_length=max_length)
    test_dataset = TranslationDataset(test_src, test_tgt, src_vocab, tgt_vocab, max_length=max_length)

    collate_fn = lambda batch: collate_translation_batch(batch, src_vocab.pad_idx, tgt_vocab.pad_idx)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        collate_fn=collate_fn,
    )
    dev_loader = DataLoader(
        dev_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        collate_fn=collate_fn,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        collate_fn=collate_fn,
    )
    return NMTData(
        train_loader=train_loader,
        dev_loader=dev_loader,
        test_loader=test_loader,
        src_vocab=src_vocab,
        tgt_vocab=tgt_vocab,
    )
