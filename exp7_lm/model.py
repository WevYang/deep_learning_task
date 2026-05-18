from __future__ import annotations

import torch
from torch import nn


class LSTMLanguageModel(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        emb_size: int = 650,
        hidden_size: int = 650,
        num_layers: int = 2,
        dropout: float = 0.5,
        tie_weights: bool = True,
        pad_idx: int = 0,
    ) -> None:
        super().__init__()
        self.encoder = nn.Embedding(vocab_size, emb_size, padding_idx=pad_idx)
        self.lstm = nn.LSTM(
            emb_size,
            hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.decoder = nn.Linear(hidden_size, vocab_size)
        if tie_weights:
            if hidden_size != emb_size:
                raise ValueError("When tying weights, emb_size must equal hidden_size.")
            self.decoder.weight = self.encoder.weight

        self.init_weights()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

    def init_weights(self) -> None:
        init_range = 0.1
        nn.init.uniform_(self.encoder.weight, -init_range, init_range)
        nn.init.zeros_(self.decoder.bias)
        nn.init.uniform_(self.decoder.weight, -init_range, init_range)

    def forward(
        self, input: torch.Tensor, hidden: tuple[torch.Tensor, torch.Tensor] | None = None
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        emb = self.dropout(self.encoder(input))
        output, hidden = self.lstm(emb, hidden)
        output = self.dropout(output)
        decoded = self.decoder(output)
        return decoded, hidden

    def init_hidden(self, batch_size: int, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
        weight = next(self.parameters())
        shape = (self.num_layers, batch_size, self.hidden_size)
        return (
            torch.zeros(shape, dtype=weight.dtype, device=device),
            torch.zeros(shape, dtype=weight.dtype, device=device),
        )
