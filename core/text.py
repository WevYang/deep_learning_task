from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Sequence

import torch


@dataclass
class Vocab:
    stoi: dict[str, int]
    itos: list[str]
    pad_token: str = "<pad>"
    unk_token: str = "<unk>"
    bos_token: str = "<bos>"
    eos_token: str = "<eos>"

    @property
    def pad_idx(self) -> int:
        return self.stoi[self.pad_token]

    @property
    def unk_idx(self) -> int:
        return self.stoi[self.unk_token]

    @property
    def bos_idx(self) -> int:
        return self.stoi[self.bos_token]

    @property
    def eos_idx(self) -> int:
        return self.stoi[self.eos_token]

    def __len__(self) -> int:
        return len(self.itos)

    def encode(self, tokens: Sequence[str]) -> list[int]:
        return [self.stoi.get(tok, self.unk_idx) for tok in tokens]

    def decode(self, ids: Sequence[int], stop_at_eos: bool = True) -> list[str]:
        tokens: list[str] = []
        for idx in ids:
            token = self.itos[int(idx)]
            if stop_at_eos and token == self.eos_token:
                break
            tokens.append(token)
        return tokens


def build_vocab_from_counter(
    counter: Counter,
    min_freq: int = 1,
    specials: Sequence[str] | None = None,
) -> Vocab:
    specials = list(specials or ["<pad>", "<unk>", "<bos>", "<eos>"])
    itos = list(dict.fromkeys(specials))
    for token, freq in counter.most_common():
        if freq >= min_freq and token not in itos:
            itos.append(token)
    stoi = {tok: i for i, tok in enumerate(itos)}
    return Vocab(stoi=stoi, itos=itos)


def pad_sequences(
    sequences: Sequence[Sequence[int]],
    pad_value: int = 0,
    max_len: int | None = None,
) -> torch.Tensor:
    if max_len is None:
        max_len = max(len(seq) for seq in sequences)
    out = torch.full((len(sequences), max_len), pad_value, dtype=torch.long)
    for i, seq in enumerate(sequences):
        trunc = list(seq)[:max_len]
        if trunc:
            out[i, : len(trunc)] = torch.tensor(trunc, dtype=torch.long)
    return out


def tokenize_text(text: str) -> list[str]:
    return text.strip().split()

