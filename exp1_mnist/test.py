from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, save_json, set_seed, write_text
from exp1_mnist.data import build_mnist_dataloaders
from exp1_mnist.model import LeNetMNIST
from exp1_mnist.train import evaluate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 1: MNIST CNN evaluation")
    parser.add_argument("--data_dir", type=str, default="data/mnist")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--save_dir", type=str, default="outputs/exp1_mnist_eval")
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)
    save_dir = ensure_dir(args.save_dir)
    dataloaders = build_mnist_dataloaders(args.data_dir, batch_size=args.batch_size, num_workers=args.num_workers)
    model = LeNetMNIST().to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt["model"])
    test_loss, test_acc = evaluate(model, dataloaders.test_loader, device)
    save_json({"test_loss": test_loss, "test_acc": test_acc, "checkpoint": args.checkpoint}, save_dir / "metrics.json")
    write_text(save_dir / "result.txt", f"test_loss={test_loss:.4f}\ntest_acc={test_acc:.4f}\n")
    print(f"test_loss={test_loss:.4f}")
    print(f"test_acc={test_acc:.4f}")


if __name__ == "__main__":
    main()
