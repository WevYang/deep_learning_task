from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import torch
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, save_json, set_seed, timestamp, write_text
from exp2_vit_cifar10.data import build_cifar10_dataloaders
from exp2_vit_cifar10.model import VisionTransformer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 2: CIFAR10 ViT training")
    parser.add_argument("--data_dir", type=str, default="data/cifar10")
    parser.add_argument("--save_dir", type=str, default="outputs/exp2_vit_cifar10")
    parser.add_argument("--batch_size", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=20)        # 从零训练 ViT 需要较多 epoch
    parser.add_argument("--lr", type=float, default=3e-4)        # AdamW 推荐学习率
    parser.add_argument("--weight_decay", type=float, default=0.05)  # ViT 正则化需要较大 weight decay
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--val_ratio", type=float, default=0.1)
    parser.add_argument("--max_train_samples", type=int, default=None)
    parser.add_argument("--max_test_samples", type=int, default=None)
    parser.add_argument("--source", type=str, default="torchvision", choices=["torchvision", "hf"])
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--amp", action="store_true")  # T4 GPU 上 AMP 可提速约 1.5x
    return parser.parse_args()


@torch.no_grad()
def evaluate(model: nn.Module, loader: torch.utils.data.DataLoader, device: torch.device) -> tuple[float, float]:
    """计算验证/测试集的平均损失和分类准确率。"""
    model.eval()
    loss_fn = nn.CrossEntropyLoss()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0
    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        logits = model(images)
        loss = loss_fn(logits, targets)
        total_loss += loss.item() * images.size(0)
        total_correct += (logits.argmax(dim=1) == targets).sum().item()
        total_samples += images.size(0)
    return total_loss / total_samples, total_correct / total_samples


def train_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    scaler: torch.cuda.amp.GradScaler | None,
) -> tuple[float, float]:
    """训练一个 epoch，支持 AMP 混合精度，返回 (平均损失, 训练准确率)。"""
    model.train()
    loss_fn = nn.CrossEntropyLoss()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0
    for images, targets in tqdm(loader, desc="train", leave=False):
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        if scaler is not None:
            with torch.cuda.amp.autocast():
                logits = model(images)
                loss = loss_fn(logits, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            logits = model(images)
            loss = loss_fn(logits, targets)
            loss.backward()
            optimizer.step()
        total_loss += loss.item() * images.size(0)
        total_correct += (logits.argmax(dim=1) == targets).sum().item()
        total_samples += images.size(0)
    return total_loss / total_samples, total_correct / total_samples


def plot_history(history: list[dict[str, float]], save_dir: Path) -> None:
    epochs = [item["epoch"] for item in history]
    train_loss = [item["train_loss"] for item in history]
    val_loss = [item["val_loss"] for item in history]
    train_acc = [item["train_acc"] for item in history]
    val_acc = [item["val_acc"] for item in history]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(epochs, train_loss, label="train_loss")
    ax1.plot(epochs, val_loss, label="val_loss")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("loss")
    ax1.legend(loc="upper left")
    ax2 = ax1.twinx()
    ax2.plot(epochs, train_acc, "--", label="train_acc")
    ax2.plot(epochs, val_acc, "--", label="val_acc")
    ax2.set_ylabel("accuracy")
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

    dataloaders = build_cifar10_dataloaders(
        args.data_dir,
        batch_size=args.batch_size,
        val_ratio=args.val_ratio,
        num_workers=args.num_workers,
        max_train_samples=args.max_train_samples,
        max_test_samples=args.max_test_samples,
        source=args.source,
    )

    model = VisionTransformer().to(device)
    # AdamW + CosineAnnealingLR：ViT 训练的推荐组合，余弦调度避免后期振荡
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.cuda.amp.GradScaler() if (args.amp and device.type == "cuda") else None

    best_val_acc = 0.0
    best_path = run_dir / "best.pt"
    history: list[dict[str, float]] = []
    log_lines = [
        f"device={device}",
        f"epochs={args.epochs}",
        f"batch_size={args.batch_size}",
        f"lr={args.lr}",
    ]

    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = train_epoch(model, dataloaders.train_loader, optimizer, device, scaler)
        val_loss, val_acc = evaluate(model, dataloaders.val_loader, device)
        scheduler.step()
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
            }
        )
        log_lines.append(
            f"epoch={epoch} train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            torch.save({"model": model.state_dict(), "args": vars(args), "epoch": epoch}, best_path)

    test_loss, test_acc = evaluate(model, dataloaders.test_loader, device)
    torch.save({"model": model.state_dict(), "args": vars(args), "epoch": args.epochs}, run_dir / "last.pt")
    save_json({"history": history, "test_loss": test_loss, "test_acc": test_acc}, run_dir / "metrics.json")
    write_text(run_dir / "train.log", "\n".join(log_lines + [f"test_loss={test_loss:.4f} test_acc={test_acc:.4f}"]))
    plot_history(history, run_dir)

    print(f"best_val_acc={best_val_acc:.4f}")
    print(f"test_acc={test_acc:.4f}")
    print(f"artifacts={run_dir}")


if __name__ == "__main__":
    main()
