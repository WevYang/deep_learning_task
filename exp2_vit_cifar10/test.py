from __future__ import annotations

import argparse
import sys

import torch

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, save_json, set_seed, write_text
from exp2_vit_cifar10.data import build_cifar10_dataloaders
from exp2_vit_cifar10.model import VisionTransformer
from exp2_vit_cifar10.train import evaluate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 2: CIFAR10 ViT evaluation")
    parser.add_argument("--data_dir", type=str, default="data/cifar10")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--save_dir", type=str, default="outputs/exp2_vit_cifar10_eval")
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--max_test_samples", type=int, default=None)
    parser.add_argument("--source", type=str, default="torchvision", choices=["torchvision", "hf"])
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)
    save_dir = ensure_dir(args.save_dir)
    dataloaders = build_cifar10_dataloaders(
        args.data_dir,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        max_test_samples=args.max_test_samples,
        source=args.source,
    )
    model = VisionTransformer().to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt["model"])
    test_loss, test_acc = evaluate(model, dataloaders.test_loader, device)
    save_json({"test_loss": test_loss, "test_acc": test_acc, "checkpoint": args.checkpoint}, save_dir / "metrics.json")
    write_text(save_dir / "result.txt", f"test_loss={test_loss:.4f}\ntest_acc={test_acc:.4f}\n")
    print(f"test_loss={test_loss:.4f}")
    print(f"test_acc={test_acc:.4f}")


if __name__ == "__main__":
    main()
