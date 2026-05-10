#!/usr/bin/env python3
"""Test runner: installs an optional wheel, then runs the test suite."""
from __future__ import annotations

import glob as _glob
import os
import platform
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f"[test] {msg}", flush=True)


def find_av_dir() -> Path:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "-f", "av"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log("pip show av failed:\n" + result.stderr)
        sys.exit(1)

    location: str | None = None
    for line in result.stdout.splitlines():
        if line.startswith("Location:"):
            location = line[len("Location:"):].strip()
            break

    if not location:
        log("Could not determine av package location via pip show")
        sys.exit(1)

    av_dir = Path(location) / "av"
    if not av_dir.is_dir():
        log(f"av directory not found at {av_dir}")
        sys.exit(1)
    return av_dir.resolve()


def run_tests(av_dir: Path) -> None:
    test_script = Path(__file__).with_name("test_impl.py")

    env = os.environ.copy()
    system = platform.system()
    if system == "Linux":
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{av_dir}:{existing}" if existing else str(av_dir)
        log(f"LD_LIBRARY_PATH prepended with {av_dir}")
    elif system == "Windows":
        existing = env.get("PATH", "")
        env["PATH"] = f"{av_dir};{existing}" if existing else str(av_dir)

    result = subprocess.run(
        [sys.executable, os.fspath(test_script)],
        capture_output=True, text=True, env=env,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        log("STDERR:\n" + result.stderr)
        sys.exit(1)


def resolve_wheel_path(arg: str) -> Path:
    if "*" in arg or "?" in arg:
        matches = _glob.glob(arg)
        if not matches:
            log(f"No files matched: {arg}")
            sys.exit(1)
        return Path(matches[-1])
    return Path(arg)


def main() -> None:
    wheel_path: str | None = sys.argv[1] if len(sys.argv) > 1 else None

    if wheel_path:
        whl = resolve_wheel_path(wheel_path)
        log(f"Installing wheel: {whl.name}  ({whl.stat().st_size / 1024 / 1024:.1f} MB)")
        subprocess.check_call([sys.executable, "-m", "pip", "install", os.fspath(whl)])

    av_dir = find_av_dir()
    log(f"av installation directory: {av_dir}")
    run_tests(av_dir)
    log("All tests passed!")


if __name__ == "__main__":
    main()
