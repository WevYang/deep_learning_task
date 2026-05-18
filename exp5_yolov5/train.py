from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, save_json, set_seed, timestamp, write_text
from exp5_yolov5.utils import ensure_yolov5_repo, run_yolov5_script


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 5: YOLOv5 training wrapper")
    parser.add_argument("--repo_dir", type=str, default="third_party/yolov5")
    parser.add_argument("--data", type=str, default=None, help="Path to a YOLOv5 data yaml file.")
    parser.add_argument("--weights", type=str, default="yolov5s.pt")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--project", type=str, default="outputs/exp5_yolov5")
    parser.add_argument("--name", type=str, default=None)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--cache", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)
    repo_dir = ensure_yolov5_repo(args.repo_dir)
    project_dir = ensure_dir(args.project)
    run_name = args.name or timestamp()
    run_dir = ensure_dir(project_dir / run_name)
    log_file = run_dir / "train.log"
    data_yaml = args.data or str(repo_dir / "data" / "coco128.yaml")
    device_arg = "cpu" if device.type == "cpu" else str(device.index if device.index is not None else 0)

    script_args = [
        "--weights",
        args.weights,
        "--data",
        data_yaml,
        "--imgsz",
        str(args.imgsz),
        "--batch-size",
        str(args.batch_size),
        "--epochs",
        str(args.epochs),
        "--project",
        str(run_dir),
        "--name",
        "run",
        "--device",
        device_arg,
        "--workers",
        str(args.workers),
        "--exist-ok",
    ]
    if args.cache:
        script_args.append("--cache")

    run_yolov5_script(repo_dir, "train.py", script_args, log_file=log_file)

    official_run = run_dir / "run"
    weights_dir = official_run / "weights"
    best_pt = weights_dir / "best.pt"
    last_pt = weights_dir / "last.pt"
    if best_pt.exists():
        shutil.copy2(best_pt, run_dir / "best.pt")
    if last_pt.exists():
        shutil.copy2(last_pt, run_dir / "last.pt")
    results_csv = official_run / "results.csv"
    if results_csv.exists():
        shutil.copy2(results_csv, run_dir / "results.csv")
    save_json(
        {
            "repo_dir": str(repo_dir),
            "data": data_yaml,
            "weights": args.weights,
            "official_run": str(official_run),
            "best_pt": str(run_dir / "best.pt") if best_pt.exists() else None,
            "last_pt": str(run_dir / "last.pt") if last_pt.exists() else None,
            "results_csv": str(run_dir / "results.csv") if results_csv.exists() else None,
            "device": str(device),
            "epochs": args.epochs,
            "imgsz": args.imgsz,
            "batch_size": args.batch_size,
        },
        run_dir / "run_info.json",
    )
    write_text(run_dir / "README.txt", f"YOLOv5 training run stored under {official_run}\n")
    print(f"artifact_dir={run_dir}")
    if best_pt.exists():
        print(f"best_pt={run_dir / 'best.pt'}")
    if results_csv.exists():
        print(f"results_csv={run_dir / 'results.csv'}")


if __name__ == "__main__":
    main()
