from __future__ import annotations

import shutil
import tarfile
import time
import urllib.request
import zipfile
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import URLError

from .utils import ensure_dir


def download_file(url: str, dst: str | Path, overwrite: bool = False, retries: int = 5) -> Path:
    dst = Path(dst)
    ensure_dir(dst.parent)
    if dst.exists() and not overwrite:
        return dst
    tmp = dst.with_suffix(dst.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            if tmp.exists():
                start = tmp.stat().st_size
                headers = {"Range": f"bytes={start}-"} if start > 0 else {}
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=60) as response:
                    status = getattr(response, "status", None)
                    if start > 0 and status != 206:
                        tmp.unlink()
                        start = 0
                        request = urllib.request.Request(url)
                        with urllib.request.urlopen(request, timeout=60) as response2, tmp.open("wb") as f:
                            shutil.copyfileobj(response2, f)
                    else:
                        mode = "ab" if start > 0 else "wb"
                        with tmp.open(mode) as f:
                            shutil.copyfileobj(response, f)
            else:
                if dst.exists():
                    dst.rename(tmp)
                else:
                    ensure_dir(tmp.parent)
                if tmp.exists() and tmp.stat().st_size > 0:
                    continue
                with urllib.request.urlopen(url, timeout=60) as response, tmp.open("wb") as f:
                    shutil.copyfileobj(response, f)
            break
        except (IncompleteRead, TimeoutError, URLError) as exc:
            last_error = exc
            if attempt == retries:
                raise
            time.sleep(min(2 * attempt, 10))
    if last_error is not None and not tmp.exists():
        raise last_error
    tmp.replace(dst)
    return dst


def extract_archive(archive: str | Path, dst_dir: str | Path) -> Path:
    archive = Path(archive)
    dst_dir = ensure_dir(dst_dir)
    suffixes = archive.suffixes
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dst_dir)
    elif suffixes[-2:] == [".tar", ".gz"] or archive.suffix in {".tgz", ".tar"}:
        mode = "r:gz" if ".gz" in suffixes else "r:"
        with tarfile.open(archive, mode) as tf:
            tf.extractall(dst_dir)
    else:
        raise ValueError(f"Unsupported archive format: {archive}")
    return dst_dir
