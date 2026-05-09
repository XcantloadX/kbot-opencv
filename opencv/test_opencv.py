#!/usr/bin/env python3
"""Test an installed OpenCV wheel for correctness."""

from __future__ import annotations

import glob as _glob
import os
import platform
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f"[test] {msg}", flush=True)


def find_cv2_dir() -> Path:
    """Find the cv2 package directory via pip show (avoids importing cv2)."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "-f", "opencv-python"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log("STDERR: " + result.stderr)
        sys.exit(1)

    lines = result.stdout.splitlines()
    location = None
    for line in lines:
        if line.startswith("Location:"):
            location = line[len("Location:"):].strip()
            break

    if not location:
        log("Could not find opencv-python location via pip show")
        sys.exit(1)

    cv2_dir = Path(location) / "cv2"
    if not cv2_dir.is_dir():
        log(f"cv2 directory not found at {cv2_dir}")
        sys.exit(1)

    return cv2_dir.resolve()


def test_installed_opencv() -> None:
    test_script = Path(__file__).with_name("test_impl.py")
    cv2_dir = find_cv2_dir()
    log(f"cv2 installation directory: {cv2_dir}")

    env = os.environ.copy()
    system = platform.system()
    if system == "Linux":
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{cv2_dir}:{existing}" if existing else str(cv2_dir)
        log(f"Set LD_LIBRARY_PATH={cv2_dir}")
    elif system == "Windows":
        existing = env.get("PATH", "")
        env["PATH"] = f"{cv2_dir};{existing}" if existing else str(cv2_dir)

    result = subprocess.run([sys.executable, os.fspath(test_script)],
                            capture_output=True, text=True, env=env)
    print(result.stdout, end="")
    if result.returncode != 0:
        log("STDERR: " + result.stderr)
        sys.exit(1)


def resolve_wheel_path(arg: str) -> Path:
    if "*" in arg or "?" in arg:
        matches = _glob.glob(arg)
        if not matches:
            log(f"No matches for: {arg}")
            sys.exit(1)
        return Path(matches[-1])
    return Path(arg)


def main() -> None:
    wheel_path: str | None = None
    if len(sys.argv) > 1:
        wheel_path = sys.argv[1]

    if wheel_path:
        whl = resolve_wheel_path(wheel_path)
        log(f"Installing wheel: {whl.name} ({whl.stat().st_size / 1024 / 1024:.1f} MB)")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            os.fspath(whl)
        ])

    test_installed_opencv()
    log("All tests passed!")


if __name__ == "__main__":
    main()
