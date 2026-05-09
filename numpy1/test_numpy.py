#!/usr/bin/env python3
"""Test an installed NumPy for correctness and absence of OpenBLAS."""

from __future__ import annotations

import glob as _glob
import os
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f"[test] {msg}", flush=True)


def test_installed_numpy() -> None:
    test_script = Path(__file__).with_name("test_impl.py")
    result = subprocess.run([sys.executable, os.fspath(test_script)],
                            capture_output=True, text=True)
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

    test_installed_numpy()
    log("All tests passed!")


if __name__ == "__main__":
    main()
