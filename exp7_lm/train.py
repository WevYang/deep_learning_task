from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import torch
from torch import nn
from torch.nn.utils import clip_grad_norm_
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, save_json, set_seed, timestamp, write_text
from exp7_lm.data import batchify, build_ptb_vocab, encode_tokens, get_batch, load_ptb_corpus
from exp7_lm.model import LSTMLanguageModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 7: PTB LSTM language model training")
    parser.add_argument("--data_dir", type=str, default="data/ptb")
    parser.add_argument("--save_dir", type=str, default="outputs/exp7_lm")
    parser.add_argument("--batch_size", type=int, default=20)
    parser.add_argument("--bptt", type=int, default=35)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-6)
    parser.add_argument("--emb_size", type=int, default=650)
    parser.add_argument("--hidden_size", type=int, default=650)
    parser.add_argument("--num_layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.5)
    parser.add_argument("--grad_clip", type=float, default=0.25)
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--amp", action="store_true")
    return parser.parse_args()


def repackage_hidden(hidden: tuple[torch.Tensor, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    return tuple(h.detach() for h in hidden)  # type: ignore[return-value]


@torch.no_grad()
def evaluate(
    model: nn.Module,
    data_source: torch.Tensor,
    device: torch.device,
    bptt: int,
    criterion: nn.Module,
) -> float:
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    hidden = model.init_hidden(data_source.size(1), device)
    for i in range(0, data_source.size(0) - 1, bptt):
        data, targets = get_batch(data_source, i, bptt)
        data = data.to(device)
        targets = targets.to(device)
        output, hidden = model(data, hidden)
        hidden = repackage_hidden(hidden)
        loss = criterion(output.reshape(-1, output.size(-1)), targets)
        total_loss += loss.item() * targets.numel()
        total_tokens += targets.numel()
    return total_loss / total_tokens


def train_epoch(
    model: nn.Module,
    train_data: torch.Tensor,
    device: torch.device,
    bptt: int,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    grad_clip: float,
    scaler: torch.cuda.amp.GradScaler | None,
) -> float:
    model.train()
    total_loss = 0.0
    total_tokens = 0
    hidden = model.init_hidden(train_data.size(1), device)
    for i in tqdm(range(0, train_data.size(0) - 1, bptt), desc="train", leave=False):
        data, targets = get_batch(train_data, i, bptt)
        data = data.to(device)
        targets = targets.to(device)
        hidden = repackage_hidden(hidden)
        optimizer.zero_grad(set_to_none=True)
        if scaler is not None:
            with torch.cuda.amp.autocast():
                output, hidden = model(data, hidden)
                loss = criterion(output.reshape(-1, output.size(-1)), targets)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            clip_grad_norm_(model.parameters(), grad_clip)
            scaler.step(optimizer)
            scaler.update()
        else:
            output, hidden = model(data, hidden)
            loss = criterion(output.reshape(-1, output.size(-1)), targets)
            loss.backward()
            clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()
        total_loss += loss.item() * targets.numel()
        total_tokens += targets.numel()
    return total_loss / total_tokens


def plot_history(history: list[dict[str, float]], save_dir: Path) -> None:
    epochs = [item["epoch"] for item in history]
    train_ppl = [item["train_ppl"] for item in history]
    val_ppl = [item["val_ppl"] for item in history]
    train_loss = [item["train_loss"] for item in history]
    val_loss = [item["val_loss"] for item in history]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(epochs, train_loss, label="train_loss")
    ax1.plot(epochs, val_loss, label="val_loss")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("loss")
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(epochs, train_ppl, "--", label="train_ppl")
    ax2.plot(epochs, val_ppl, "--", label="val_ppl")
    ax2.set_ylabel("perplexity")
    ax2.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(save_dir / "training_curve.png", dpi=160)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)
    save_dir = ensure_dir(args.save_dir)
    run_dir = ensure_dir(save_dir / timestamp())

    train_tokens, valid_tokens, test_tokens = load_ptb_corpus(args.data_dir)
    vocab = build_ptb_vocab(train_tokens)
    train_data = batchify(encode_tokens(train_tokens, vocab), args.batch_size)
    valid_data = batchify(encode_tokens(valid_tokens, vocab), args.batch_size)
    test_data = batchify(encode_tokens(test_tokens, vocab), args.batch_size)

    model = LSTMLanguageModel(
        vocab_size=len(vocab),
        emb_size=args.emb_size,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
        tie_weights=True,
        pad_idx=vocab.pad_idx,
    ).to(device)
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = nn.CrossEntropyLoss()
    scaler = torch.cuda.amp.GradScaler() if (args.amp and device.type == "cuda") else None

    history: list[dict[str, float]] = []
    best_val_loss = float("inf")
    best_path = run_dir / "best.pt"
    log_lines = [f"device={device}", f"epochs={args.epochs}", f"batch_size={args.batch_size}", f"bptt={args.bptt}"]

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(
            model,
            train_data,
            device,
            args.bptt,
            criterion,
            optimizer,
            args.grad_clip,
            scaler,
        )
        val_loss = evaluate(model, valid_data, device, args.bptt, criterion)
        scheduler.step()
        train_ppl = math.exp(train_loss)
        val_ppl = math.exp(val_loss)
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": train_loss,
                "val_loss": val_loss,
                "train_ppl": train_ppl,
                "val_ppl": val_ppl,
            }
        )
        log_lines.append(
            f"epoch={epoch} train_loss={train_loss:.4f} val_loss={val_loss:.4f} "
            f"train_ppl={train_ppl:.2f} val_ppl={val_ppl:.2f}"
        )
        if val_loss <= best_val_loss:
            best_val_loss = val_loss
            torch.save(
                {
                    "model": model.state_dict(),
                    "vocab": {
                        "stoi": vocab.stoi,
                        "itos": vocab.itos,
                        "pad_token": vocab.pad_token,
                        "unk_token": vocab.unk_token,
                        "bos_token": vocab.bos_token,
                        "eos_token": vocab.eos_token,
                    },
                    "args": vars(args),
                    "epoch": epoch,
                },
                best_path,
            )

    test_loss = evaluate(model, test_data, device, args.bptt, criterion)
    test_ppl = math.exp(test_loss)
    torch.save({"model": model.state_dict(), "vocab": vocab.__dict__, "args": vars(args)}, run_dir / "last.pt")
    save_json({"history": history, "best_val_loss": best_val_loss, "test_loss": test_loss, "test_ppl": test_ppl}, run_dir / "metrics.json")
    write_text(run_dir / "train.log", "\n".join(log_lines + [f"test_loss={test_loss:.4f} test_ppl={test_ppl:.2f}"]))
    plot_history(history, run_dir)
    print(f"best_val_loss={best_val_loss:.4f}")
    print(f"test_ppl={test_ppl:.2f}")
    print(f"artifacts={run_dir}")


if __name__ == "__main__":
    main()
