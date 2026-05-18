from __future__ import annotations

import math
from typing import Iterable, Sequence

import torch
from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu


def accuracy(logits: torch.Tensor, targets: torch.Tensor) -> float:
    preds = logits.argmax(dim=-1)
    return (preds == targets).float().mean().item()


def compute_bleu(
    references: Sequence[Sequence[Sequence[str]]],
    hypotheses: Sequence[Sequence[str]],
) -> float:
    smoothing = SmoothingFunction().method4
    return float(corpus_bleu(references, hypotheses, smoothing_function=smoothing))


def perplexity(loss: float) -> float:
    return float(math.exp(loss))

