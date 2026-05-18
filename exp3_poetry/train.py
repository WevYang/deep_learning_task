from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import torch
from torch import nn
from torch.optim import Adam
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, save_json, set_seed, timestamp, write_text
from exp3_poetry.data import build_poetry_loaders
from exp3_poetry.model import PoetryLSTM


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 3: Poetry LSTM training")
    parser.add_argument("--data_dir", type=str, default="data/poetry")
    parser.add_argument("--save_dir", type=str, default="outputs/exp3_poetry")
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight_decay", type=float, default=1e-5)
    parser.add_argument("--embed_dim", type=int, default=256)
    parser.add_argument("--hidden_dim", type=int, default=512)
    parser.add_argument("--num_layers", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--val_ratio", type=float, default=0.05)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--amp", action="store_true")
    return parser.parse_args()


@torch.no_grad()
def evaluate(model: nn.Module, loader: torch.utils.data.DataLoader, device: torch.device, pad_idx: int) -> float:
    """计算验证集平均 token 级交叉熵（忽略 padding），用于计算困惑度 ppl=exp(loss)。"""
    model.eval()
    loss_fn = nn.CrossEntropyLoss(ignore_index=pad_idx)
    total_loss = 0.0
    total_tokens = 0
    for inputs, targets in loader:
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        logits, _ = model(inputs)
        loss = loss_fn(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
        valid = (targets != pad_idx).sum().item()
        total_loss += loss.item() * max(valid, 1)
        total_tokens += max(valid, 1)
    return total_loss / total_tokens


def train_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    pad_idx: int,
    scaler: torch.cuda.amp.GradScaler | None,
) -> float:
    model.train()
    loss_fn = nn.CrossEntropyLoss(ignore_index=pad_idx)
    total_loss = 0.0
    total_tokens = 0
    for inputs, targets in tqdm(loader, desc="train", leave=False):
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        if scaler is not None:
            with torch.cuda.amp.autocast():
                logits, _ = model(inputs)
                loss = loss_fn(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            logits, _ = model(inputs)
            loss = loss_fn(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
            loss.backward()
            optimizer.step()
        valid = (targets != pad_idx).sum().item()
        total_loss += loss.item() * max(valid, 1)
        total_tokens += max(valid, 1)
    return total_loss / total_tokens


def plot_history(history: list[dict[str, float]], save_dir: Path) -> None:
    epochs = [item["epoch"] for item in history]
    train_loss = [item["train_loss"] for item in history]
    val_loss = [item["val_loss"] for item in history]
    train_ppl = [item["train_ppl"] for item in history]
    val_ppl = [item["val_ppl"] for item in history]

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

    train_loader, val_loader, ix2word, word2ix = build_poetry_loaders(
        args.data_dir,
        batch_size=args.batch_size,
        val_ratio=args.val_ratio,
        num_workers=args.num_workers,
    )
    pad_idx = word2ix["</s>"]
    model = PoetryLSTM(
        vocab_size=len(word2ix),
        embed_dim=args.embed_dim,
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        dropout=args.dropout,
        pad_idx=pad_idx,
    ).to(device)
    optimizer = Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    # GradScaler 在 GPU + AMP 模式下防止 fp16 梯度下溢
    scaler = torch.cuda.amp.GradScaler() if (args.amp and device.type == "cuda") else None

    history: list[dict[str, float]] = []
    best_val_loss = float("inf")
    best_path = run_dir / "best.pt"
    log_lines = [f"device={device}", f"epochs={args.epochs}", f"batch_size={args.batch_size}"]

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device, pad_idx, scaler)
        val_loss = evaluate(model, val_loader, device, pad_idx)
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
                    "ix2word": ix2word,
                    "word2ix": word2ix,
                    "args": vars(args),
                    "epoch": epoch,
                },
                best_path,
            )

    torch.save({"model": model.state_dict(), "ix2word": ix2word, "word2ix": word2ix, "args": vars(args)}, run_dir / "last.pt")
    save_json({"history": history, "best_val_loss": best_val_loss}, run_dir / "metrics.json")
    write_text(run_dir / "train.log", "\n".join(log_lines))
    plot_history(history, run_dir)
    print(f"best_val_loss={best_val_loss:.4f}")
    print(f"artifacts={run_dir}")


if __name__ == "__main__":
    main()
