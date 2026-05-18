from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from core import ensure_dir


YOLOV5_REPO_URL = "https://github.com/ultralytics/yolov5.git"


def ensure_yolov5_repo(repo_dir: str | Path) -> Path:
    repo_dir = Path(repo_dir)
    if not (repo_dir / "train.py").exists():
        ensure_dir(repo_dir.parent)
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        subprocess.run(
            ["git", "clone", "--depth", "1", YOLOV5_REPO_URL, str(repo_dir)],
            check=True,
        )
    sentinel = repo_dir / ".codex_requirements_installed"
    if not sentinel.exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=repo_dir, check=True)
        sentinel.write_text("installed\n", encoding="utf-8")
    return repo_dir


def run_yolov5_script(repo_dir: str | Path, script: str, args: list[str], log_file: Path | None = None) -> None:
    repo_dir = Path(repo_dir)
    cmd = [sys.executable, script, *args]
    if log_file is None:
        subprocess.run(cmd, cwd=repo_dir, check=True)
        return
    ensure_dir(log_file.parent)
    with log_file.open("w", encoding="utf-8") as f:
        subprocess.run(cmd, cwd=repo_dir, check=True, stdout=f, stderr=subprocess.STDOUT)

