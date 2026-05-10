#!/usr/bin/env python3
"""Build a minimal PyAV wheel against a custom-configured FFmpeg.

On Linux  : clones FFmpeg, builds it from source, then builds PyAV.
On Windows: FFmpeg must be pre-built via MSYS2 (done in the workflow);
            this script only handles the PyAV build and wheel repair.

Environment variables
---------------------
FFMPEG_VERSION      FFmpeg git tag to clone  (default: n7.1)
PYAV_VERSION        PyAV release version     (default: 14.3.0)
FFMPEG_INSTALL_DIR  Path to pre-built FFmpeg install prefix (Windows required)
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SYSTEM: str = platform.system()
MACHINE: str = platform.machine()

# FFmpeg configure flags that apply on every platform.
# Libraries beyond the user-requested set are required by PyAV's build system.
FFMPEG_CONFIGURE_FLAGS: list[str] = [
    "--disable-everything",
    "--disable-programs",
    "--disable-doc",
    "--enable-shared",
    "--disable-static",
    # Library frameworks required by PyAV (compiled as mostly-empty shells
    # when everything else is disabled, but the headers + link targets must exist)
    "--enable-avcodec",
    "--enable-avformat",
    "--enable-avdevice",
    "--enable-avutil",
    "--enable-avfilter",
    "--enable-swscale",
    "--enable-swresample",
    # Minimal codec set: H.264 decode only
    "--enable-decoder=h264",
    "--enable-parser=h264",
    "--enable-bsf=h264_mp4toannexb",
]


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def run(cmd: list[str] | str, **kwargs) -> None:
    if isinstance(cmd, list):
        log(f"+ {subprocess.list2cmdline(cmd)}")
    else:
        log(f"+ {cmd}")
    subprocess.check_call(cmd, **kwargs)


def nproc() -> int:
    return os.cpu_count() or 4


# ---------------------------------------------------------------------------
# FFmpeg build (Linux only — Windows uses MSYS2 shell in the workflow)
# ---------------------------------------------------------------------------

def build_ffmpeg_linux(ffmpeg_src: Path, ffmpeg_install: Path, version: str) -> None:
    if not ffmpeg_src.exists():
        log(f"Cloning FFmpeg {version}…")
        run(["git", "clone", "--depth", "1", "--branch", version,
             "https://git.ffmpeg.org/ffmpeg.git", str(ffmpeg_src)])

    if ffmpeg_install.exists():
        shutil.rmtree(ffmpeg_install)
    ffmpeg_install.mkdir(parents=True)

    flags = FFMPEG_CONFIGURE_FLAGS + [f"--prefix={ffmpeg_install}"]
    configure = "./configure " + " ".join(flags)
    script = f"{configure} && make -j{nproc()} && make install"

    log("Configuring and building FFmpeg…")
    run(["bash", "-c", script], cwd=ffmpeg_src)
    log(f"FFmpeg installed to: {ffmpeg_install}")


# ---------------------------------------------------------------------------
# PyAV build (both platforms)
# ---------------------------------------------------------------------------

def ensure_msvc_import_libs(ffmpeg_install: Path) -> None:
    """Create MSVC-compatible import .lib files from FFmpeg DLLs.

    When FFmpeg is built inside MSYS2 with GNU ld (even with --toolchain=msvc),
    the import libraries may be emitted as MinGW-style .dll.a files rather than
    MSVC-style .lib files.  MSVC's link.exe requires .lib files, so we generate
    them post-build using dumpbin + lib.exe.
    """
    import re

    lib_dir = ffmpeg_install / "lib"
    bin_dir = ffmpeg_install / "bin"
    lib_dir.mkdir(exist_ok=True)

    ff_libs = [
        "avformat", "avcodec", "avdevice",
        "avutil", "avfilter", "swscale", "swresample",
    ]

    # Print what's actually there for diagnostics
    log("--- ffmpeg_install/lib contents ---")
    for f in sorted(lib_dir.iterdir()) if lib_dir.exists() else []:
        log(f"  {f.name}")
    log("--- ffmpeg_install/bin contents ---")
    for f in sorted(bin_dir.iterdir()) if bin_dir.exists() else []:
        log(f"  {f.name}")

    for lib_name in ff_libs:
        lib_file = lib_dir / f"{lib_name}.lib"
        if lib_file.exists():
            log(f"  {lib_name}.lib already present — skipping")
            continue

        dlls = list(bin_dir.glob(f"{lib_name}-*.dll"))
        if not dlls:
            log(f"  WARNING: no {lib_name}-*.dll found in {bin_dir}")
            continue
        dll = dlls[0]
        log(f"  Creating MSVC import lib for {dll.name}…")

        result = subprocess.run(
            ["dumpbin", "/EXPORTS", str(dll)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            log(f"  WARNING: dumpbin failed for {dll.name}: {result.stderr[:200]}")
            continue

        exports: list[str] = []
        for line in result.stdout.splitlines():
            m = re.match(r"\s+\d+\s+[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+(\w+)", line)
            if m:
                exports.append(m.group(1))

        if not exports:
            log(f"  WARNING: no exports found in {dll.name}")
            continue

        def_file = lib_dir / f"{lib_name}.def"
        def_content = f"LIBRARY {dll.name}\nEXPORTS\n" + "\n".join(exports) + "\n"
        def_file.write_text(def_content, encoding="ascii")

        run(["lib", "/MACHINE:X64", f"/DEF:{def_file}", f"/OUT:{lib_file}", "/NOLOGO"])
        def_file.unlink(missing_ok=True)
        log(f"  Created {lib_file.name}")


def build_pyav(
    pyav_src: Path,
    dist_dir: Path,
    ffmpeg_install: Path,
    version: str,
) -> None:
    if not pyav_src.exists():
        log(f"Cloning PyAV v{version}…")
        run(["git", "clone", "--depth", "1", "--branch", f"v{version}",
             "https://github.com/PyAV-Org/PyAV.git", str(pyav_src)])

    dist_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    if SYSTEM == "Windows":
        inc = str(ffmpeg_install / "include")
        lib = str(ffmpeg_install / "lib")
        env["INCLUDE"] = inc + ";" + env.get("INCLUDE", "")
        env["LIB"] = lib + ";" + env.get("LIB", "")
        log(f"INCLUDE={env['INCLUDE'][:80]}…")
        log(f"LIB={env['LIB'][:80]}…")
    else:
        pkg_path = str(ffmpeg_install / "lib" / "pkgconfig")
        env["PKG_CONFIG_PATH"] = pkg_path + ":" + env.get("PKG_CONFIG_PATH", "")
        env["LD_LIBRARY_PATH"] = (
            str(ffmpeg_install / "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
        )
        log(f"PKG_CONFIG_PATH={env['PKG_CONFIG_PATH']}")

    log(f"Building PyAV wheel (cwd={pyav_src})…")
    run(
        [sys.executable, "-m", "pip", "wheel", str(pyav_src),
         "--no-deps", "-w", str(dist_dir)],
        env=env,
    )


def repair_wheel(dist_dir: Path, ffmpeg_install: Path) -> None:
    wheels = list(dist_dir.glob("av-*.whl"))
    if not wheels:
        log("ERROR: No av-*.whl found in dist/")
        sys.exit(1)
    whl = wheels[0]
    log(f"Repairing wheel: {whl.name}")

    if SYSTEM == "Windows":
        run([sys.executable, "-m", "pip", "install", "delvewheel"])
        repaired_dir = dist_dir / "_repaired"
        repaired_dir.mkdir(exist_ok=True)
        ffmpeg_bin = str(ffmpeg_install / "bin")
        run([sys.executable, "-m", "delvewheel", "repair",
             str(whl), "--add-path", ffmpeg_bin, "-w", str(repaired_dir)])
        # Delete the original (unrepaired) wheel BEFORE moving the repaired one
        # in — both have the same filename so we must clear the dest first.
        whl.unlink(missing_ok=True)
        for w in repaired_dir.glob("*.whl"):
            shutil.move(str(w), str(dist_dir / w.name))
        shutil.rmtree(repaired_dir, ignore_errors=True)
    else:
        run([sys.executable, "-m", "pip", "install", "auditwheel"])
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = (
            str(ffmpeg_install / "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
        )
        run([sys.executable, "-m", "auditwheel", "repair",
             str(whl), "-w", str(dist_dir)], env=env)
        whl.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ffmpeg_version: str = os.environ.get("FFMPEG_VERSION", "n7.1")
    pyav_version: str = os.environ.get("PYAV_VERSION", "14.3.0")

    root: Path = Path.cwd()
    ffmpeg_src: Path = root / "ffmpeg_src"
    pyav_src: Path = root / "pyav_src"
    dist_dir: Path = root / "dist"

    log(f"Python  : {sys.executable}")
    log(f"System  : {SYSTEM} {MACHINE}")
    log(f"FFmpeg  : {ffmpeg_version}")
    log(f"PyAV    : {pyav_version}")

    # Resolve the FFmpeg install prefix
    ffmpeg_install_env: str | None = os.environ.get("FFMPEG_INSTALL_DIR")
    if ffmpeg_install_env:
        ffmpeg_install = Path(ffmpeg_install_env)
        log(f"Using pre-built FFmpeg at: {ffmpeg_install}")
        if not ffmpeg_install.is_dir():
            log("ERROR: FFMPEG_INSTALL_DIR does not exist or is not a directory")
            sys.exit(1)
    else:
        ffmpeg_install = root / "ffmpeg_install"
        if SYSTEM == "Linux":
            build_ffmpeg_linux(ffmpeg_src, ffmpeg_install, ffmpeg_version)
        else:
            log(
                "ERROR: On Windows, set FFMPEG_INSTALL_DIR to a pre-built FFmpeg prefix.\n"
                "       The workflow should build FFmpeg via MSYS2 and export that path."
            )
            sys.exit(1)

    # On Windows the MSYS2 build may produce MinGW-style .dll.a import libs
    # instead of MSVC-style .lib files.  Generate any missing .lib from the DLLs.
    if SYSTEM == "Windows":
        log("Ensuring MSVC import libs exist...")
        ensure_msvc_import_libs(ffmpeg_install)

    # Install build dependencies for PyAV
    run([sys.executable, "-m", "pip", "install",
         "cython>=3.0", "setuptools>=77", "wheel"])

    build_pyav(pyav_src, dist_dir, ffmpeg_install, pyav_version)
    repair_wheel(dist_dir, ffmpeg_install)

    log(f"Done! Artifacts in: {dist_dir}")
    for w in sorted(dist_dir.glob("*.whl")):
        log(f"  {w.name}  ({w.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
