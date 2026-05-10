#!/usr/bin/env python3
"""Test an installed PySide6 slim wheel for correctness."""
from __future__ import annotations

import glob as _glob
import os
import subprocess
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(f"[test] {msg}", flush=True)


def resolve_wheel(arg: str) -> Path:
    if "*" in arg or "?" in arg:
        matches = _glob.glob(arg)
        if not matches:
            log(f"No matches for glob: {arg}")
            sys.exit(1)
        return Path(matches[-1])
    return Path(arg)


def main() -> None:
    if len(sys.argv) > 1:
        whl = resolve_wheel(sys.argv[1])
        log(f"Installing: {whl.name}  ({whl.stat().st_size / 1024 / 1024:.1f} MB)")
        subprocess.check_call([sys.executable, "-m", "pip", "install", os.fspath(whl)])

    test_script = Path(__file__).with_name("test_impl.py")
    env = os.environ.copy()
    # Use offscreen Qt platform so tests run without a display
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    result = subprocess.run(
        [sys.executable, os.fspath(test_script)],
        capture_output=True, text=True, env=env,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        log("STDERR:\n" + result.stderr)
        sys.exit(1)

    log("All tests passed!")


if __name__ == "__main__":
    main()
