#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SYSTEM: str = platform.system()
MACHINE: str = platform.machine()


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def run(cmd: list[str] | str, **kwargs) -> None:
    if isinstance(cmd, list):
        log(f"+ {subprocess.list2cmdline(cmd)}")
    else:
        log(f"+ {cmd}")
    subprocess.check_call(cmd, **kwargs)


def main() -> None:
    python_exe: Path = Path(sys.executable).resolve()
    numpy_version: str = os.environ.get("NUMPY_VERSION", "1.26.4")
    root: Path = Path.cwd()
    src_dir: Path = root / "numpy-src"
    dist_dir: Path = root / "dist"

    log(f"Python: {python_exe}")
    log(f"NumPy version: {numpy_version}")
    log(f"System: {SYSTEM} {MACHINE}")

    # ---- Install build dependencies ----
    run([str(python_exe), "-m", "pip", "install",
         "Cython>=0.29.34,<3.1",
         "meson-python>=0.15.0,<0.16.0",
         "ninja"])

    # ---- Clone NumPy source (with submodules for vendored meson) ----
    if src_dir.exists():
        shutil.rmtree(src_dir)
    run(["git", "clone", "--depth", "1", "--branch", f"v{numpy_version}",
         "https://github.com/numpy/numpy.git", str(src_dir)])
    run(["git", "submodule", "update", "--init", "--depth", "1"],
        cwd=src_dir)

    # ---- Build wheel ----
    dist_dir.mkdir(parents=True, exist_ok=True)

    config_settings: list[str] = [
        "-C", "setup-args=-Dallow-noblas=true",
    ]
    if SYSTEM == "Windows":
        config_settings += ["-C", "setup-args=--vsenv"]

    pip_wheel_args: list[str] = [
        str(python_exe), "-m", "pip", "wheel",
        "--no-deps",
        "-w", str(dist_dir),
        str(src_dir),
    ] + config_settings

    env = os.environ.copy()
    if SYSTEM == "Windows":
        env["CC"] = "cl.exe"
        env["CXX"] = "cl.exe"

    run(pip_wheel_args, env=env)

    log(f"Done! Artifacts in: {dist_dir}")
    for w in sorted(dist_dir.glob("*.whl")):
        size_mb = w.stat().st_size / 1024 / 1024
        log(f"  {w.name}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
