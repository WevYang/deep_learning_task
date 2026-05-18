from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import ensure_dir, get_device, save_json, set_seed, timestamp, write_text
from exp5_yolov5.utils import ensure_yolov5_repo, run_yolov5_script


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Experiment 5: YOLOv5 inference wrapper")
    parser.add_argument("--repo_dir", type=str, default="third_party/yolov5")
    parser.add_argument("--weights", type=str, required=True)
    parser.add_argument("--source", type=str, default=None)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf_thres", type=float, default=0.25)
    parser.add_argument("--project", type=str, default="outputs/exp5_yolov5_pred")
    parser.add_argument("--name", type=str, default=None)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)
    repo_dir = ensure_yolov5_repo(args.repo_dir)
    project_dir = ensure_dir(args.project)
    run_name = args.name or timestamp()
    run_dir = ensure_dir(project_dir / run_name)
    log_file = run_dir / "predict.log"
    source = args.source or str(repo_dir / "data" / "images" / "bus.jpg")
    device_arg = "cpu" if device.type == "cpu" else str(device.index if device.index is not None else 0)

    script_args = [
        "--weights",
        args.weights,
        "--source",
        source,
        "--imgsz",
        str(args.imgsz),
        "--conf-thres",
        str(args.conf_thres),
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
    run_yolov5_script(repo_dir, "detect.py", script_args, log_file=log_file)

    official_run = run_dir / "run"
    predictions = list(official_run.glob("*")) if official_run.exists() else []
    save_json(
        {
            "repo_dir": str(repo_dir),
            "weights": args.weights,
            "source": source,
            "official_run": str(official_run),
            "artifacts": [str(p) for p in predictions],
            "device": str(device),
            "imgsz": args.imgsz,
            "conf_thres": args.conf_thres,
        },
        run_dir / "run_info.json",
    )
    write_text(run_dir / "README.txt", f"YOLOv5 prediction run stored under {official_run}\n")
    print(f"artifact_dir={run_dir}")
    if official_run.exists():
        print(f"prediction_dir={official_run}")


if __name__ == "__main__":
    main()
