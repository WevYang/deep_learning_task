from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

import torch

from core import build_vocab_from_counter, download_file, ensure_dir, extract_archive, resolve_root
from core.text import Vocab, tokenize_text


PTB_URL = "http://www.fit.vutbr.cz/~imikolov/rnnlm/simple-examples.tgz"
PTB_RAW_URLS = {
    "ptb.train.txt": "https://raw.githubusercontent.com/wojzaremba/lstm/master/data/ptb.train.txt",
    "ptb.valid.txt": "https://raw.githubusercontent.com/wojzaremba/lstm/master/data/ptb.valid.txt",
    "ptb.test.txt": "https://raw.githubusercontent.com/wojzaremba/lstm/master/data/ptb.test.txt",
}


def ensure_ptb_dataset(data_dir: str | Path) -> Path:
    data_dir = ensure_dir(data_dir)
    candidates = [
        data_dir / "simple-examples",
        data_dir / "simple-examples" / "data",
        data_dir,
    ]
    for candidate in candidates:
        train = candidate / "ptb.train.txt"
        valid = candidate / "ptb.valid.txt"
        test = candidate / "ptb.test.txt"
        if train.exists() and valid.exists() and test.exists():
            return candidate

    try:
        for filename, url in PTB_RAW_URLS.items():
            download_file(url, data_dir / filename)
        if all((data_dir / name).exists() for name in PTB_RAW_URLS):
            return data_dir
    except Exception:
        pass

    archive = data_dir / "simple-examples.tgz"
    try:
        download_file(PTB_URL, archive)
        extract_archive(archive, data_dir)
    except Exception:
        if archive.exists():
            part = archive.with_suffix(archive.suffix + ".part")
            if not part.exists():
                archive.rename(part)
            else:
                archive.unlink()
        download_file(PTB_URL, archive)
        extract_archive(archive, data_dir)

    for candidate in candidates:
        train = candidate / "ptb.train.txt"
        valid = candidate / "ptb.valid.txt"
        test = candidate / "ptb.test.txt"
        if train.exists() and valid.exists() and test.exists():
            return candidate

    raise FileNotFoundError("Failed to locate PTB files after extraction.")


def _read_tokens(path: Path) -> list[str]:
    tokens: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        words = line.strip().split()
        if not words:
            continue
        tokens.extend(word.lower() for word in words)
        tokens.append("<eos>")
    return tokens


def load_ptb_corpus(data_dir: str | Path) -> tuple[list[str], list[str], list[str]]:
    root = ensure_ptb_dataset(data_dir)
    return (
        _read_tokens(root / "ptb.train.txt"),
        _read_tokens(root / "ptb.valid.txt"),
        _read_tokens(root / "ptb.test.txt"),
    )


def build_ptb_vocab(train_tokens: list[str]) -> Vocab:
    counter = Counter(train_tokens)
    return build_vocab_from_counter(counter, specials=["<pad>", "<unk>", "<bos>", "<eos>"])


def encode_tokens(tokens: list[str], vocab: Vocab) -> torch.Tensor:
    return torch.tensor(vocab.encode(tokens), dtype=torch.long)


def batchify(data: torch.Tensor, batch_size: int) -> torch.Tensor:
    nbatch = data.size(0) // batch_size
    data = data.narrow(0, 0, nbatch * batch_size)
    data = data.view(batch_size, -1).t().contiguous()
    return data


def get_batch(source: torch.Tensor, i: int, bptt: int) -> tuple[torch.Tensor, torch.Tensor]:
    seq_len = min(bptt, len(source) - 1 - i)
    data = source[i : i + seq_len]
    target = source[i + 1 : i + 1 + seq_len].reshape(-1)
    return data, target
