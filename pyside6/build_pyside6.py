#!/usr/bin/env python3
"""
Build a slimmed PySide6 wheel.

Downloads the official PySide6_Essentials wheel, prunes unused Qt modules,
and repacks it as a PySide6 wheel containing only:
  QtCore, QtGui, QtWidgets, QtQml, QtQuick, QtQuickControls2, QtSvg

Keep-list is derived from tools/prune_pyside6.py in ichikas-auto-assistant.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SYSTEM = platform.system()

# ── Modules to retain ─────────────────────────────────────────────────────
KEEP_MODULES: frozenset[str] = frozenset({
    "QtCore", "QtGui", "QtWidgets",
    "QtQml", "QtQuick", "QtQuickControls2", "QtSvg",
})

KEEP_QML_DIRS: frozenset[str] = frozenset({"QtQml", "QtQuick"})

KEEP_PLUGIN_DIRS: frozenset[str] = frozenset({
    "generic", "iconengines", "imageformats", "platforminputcontexts",
    "platforms", "renderers", "styles", "tls",
})

QML_SUBDIR_EXCLUDES: tuple[str, ...] = (
    "QtQuick/VirtualKeyboard", "QtQuick/Particles", "QtQuick/Pdf",
    "QtQuick/Scene2D", "QtQuick/Scene3D", "QtQuick/Timeline",
    "QtQuick/VectorImage", "QtQuick/tooling",
    "QtQuick/Controls/FluentWinUI3", "QtQuick/Controls/Fusion",
    "QtQuick/Controls/Imagine", "QtQuick/Controls/Material",
    "QtQuick/Controls/Universal", "QtQuick/Controls/designer",
)

PLUGIN_FILE_EXCLUDES: frozenset[str] = frozenset({
    "openglrenderer.dll", "qdirect2d.dll",
})

TOOL_EXE_STEMS: frozenset[str] = frozenset({
    "assistant", "designer", "linguist", "lupdate", "lrelease",
    "uic", "qmlformat", "qmlimportscanner", "qmllint", "qmltyperegistrar",
    "qmlcachegen", "qsb", "svgtoqml", "balsam", "balsamui", "qmlls",
    "QtWebEngineProcess",
})

REMOVE_SUBDIRS: tuple[str, ...] = (
    "translations", "include", "typesystems", "doc",
    "scripts", "support", "resources", "metatypes",
)

# DLL/SO name prefixes to always remove regardless of Qt module mapping
NON_QT_FILE_EXCLUDES: tuple[str, ...] = (
    "opengl32sw", "avcodec-", "avformat-", "avutil-", "swscale-", "swresample-",
)


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def run(cmd: list[str], **kwargs) -> None:
    log(f"+ {subprocess.list2cmdline(cmd)}")
    subprocess.check_call(cmd, **kwargs)


# ── File-name parsers ──────────────────────────────────────────────────────

def _qt_module_from_pyd(name: str) -> str | None:
    m = re.match(r"^(Qt[^.]+)\.pyd$", name)
    return m.group(1) if m else None


def _qt_module_from_dll(name: str) -> str | None:
    m = re.match(r"^Qt6(.+)\.dll$", name, re.IGNORECASE)
    return "Qt" + m.group(1) if m else None


def _qt_module_from_so_binding(name: str) -> str | None:
    # QtCore.cpython-311-x86_64-linux-gnu.so  or  QtCore.abi3.so
    m = re.match(r"^(Qt[^.]+)\.(cpython|abi3)", name)
    return m.group(1) if m else None


def _qt_module_from_so_lib(name: str) -> str | None:
    # libQt6Core.so.6  →  QtCore
    m = re.match(r"^libQt6(.+)\.so", name)
    return "Qt" + m.group(1) if m else None


# ── Pruning ────────────────────────────────────────────────────────────────

def _remove(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        size = path.stat().st_size
        path.unlink()
        return size
    size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    shutil.rmtree(path)
    return size


def prune_pyside6(pyside6_dir: Path) -> int:
    is_windows = SYSTEM == "Windows"
    removed = 0

    # 1. Explicitly wasteful non-Qt DLLs only.
    #    Python .pyd/.so binding files are NOT pruned: PySide6's type system
    #    creates Python-level import chains between modules (e.g. QtQml imports
    #    PySide6.QtNetwork at load time), and removing bindings causes
    #    ImportError for the modules we DO want to keep.
    #    Qt native DLLs/SOs are also kept for the same C++ dependency reasons.
    if is_windows:
        for f in list(pyside6_dir.glob("*.dll")):
            if any(f.name.lower().startswith(k) for k in NON_QT_FILE_EXCLUDES):
                removed += _remove(f)
    else:
        pass  # no safe per-file removals on Linux at this level

    # 2. QML directories (Windows: PySide6/qml, Linux: PySide6/Qt/qml)
    for qml_root in _qml_roots(pyside6_dir):
        if not qml_root.is_dir():
            continue
        for child in list(qml_root.iterdir()):
            if child.is_dir() and child.name not in KEEP_QML_DIRS:
                removed += _remove(child)
        for subdir in QML_SUBDIR_EXCLUDES:
            removed += _remove(qml_root / subdir)

    # 3. Plugin directories
    for plugins_root in _plugin_roots(pyside6_dir):
        if not plugins_root.is_dir():
            continue
        for child in list(plugins_root.iterdir()):
            if child.is_dir() and child.name not in KEEP_PLUGIN_DIRS:
                removed += _remove(child)
        for name in PLUGIN_FILE_EXCLUDES:
            for f in plugins_root.rglob(name):
                removed += _remove(f)

    # 4. Tool executables
    exe_suffix = ".exe" if is_windows else ""
    for stem in TOOL_EXE_STEMS:
        removed += _remove(pyside6_dir / f"{stem}{exe_suffix}")
        if not is_windows:
            removed += _remove(pyside6_dir / "Qt" / "bin" / stem)

    # 5. .pyi stubs and Windows import libs
    for f in list(pyside6_dir.glob("**/*.pyi")):
        removed += _remove(f)
    if is_windows:
        for f in list(pyside6_dir.glob("**/*.lib")):
            removed += _remove(f)

    # 6. Bulk subtree removals
    for name in REMOVE_SUBDIRS:
        removed += _remove(pyside6_dir / name)
        if not is_windows:
            removed += _remove(pyside6_dir / "Qt" / name)

    return removed


def _qml_roots(pyside6_dir: Path) -> list[Path]:
    if SYSTEM == "Windows":
        return [pyside6_dir / "qml"]
    return [pyside6_dir / "qml", pyside6_dir / "Qt" / "qml"]


def _plugin_roots(pyside6_dir: Path) -> list[Path]:
    if SYSTEM == "Windows":
        return [pyside6_dir / "plugins"]
    return [pyside6_dir / "plugins", pyside6_dir / "Qt" / "plugins"]


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    version: str = os.environ.get("PYSIDE6_VERSION", "6.8.0")
    python_exe = Path(sys.executable).resolve()

    root = Path.cwd()
    download_dir = root / "pyside6_download"
    extract_dir = root / "pyside6_extracted"
    dist_dir = root / "dist"

    log(f"Python:    {python_exe}")
    log(f"PySide6:   {version}")
    log(f"System:    {SYSTEM} {platform.machine()}")

    for d in (download_dir, extract_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
    dist_dir.mkdir(exist_ok=True)

    # ── Download ──────────────────────────────────────────────────────
    log("Downloading PySide6_Essentials (this may take a while)...")
    run([str(python_exe), "-m", "pip", "download",
         f"PySide6_Essentials=={version}",
         "--only-binary", ":all:",
         "--no-deps",
         "-d", str(download_dir)])

    wheels = list(download_dir.glob("PySide6_Essentials*.whl"))
    if not wheels:
        log("ERROR: PySide6_Essentials wheel not found after download")
        sys.exit(1)
    wheel_path = wheels[0]
    log(f"Downloaded: {wheel_path.name}  ({wheel_path.stat().st_size / 1e6:.1f} MB)")

    # ── Extract ───────────────────────────────────────────────────────
    log("Extracting wheel...")
    with zipfile.ZipFile(wheel_path, "r") as zf:
        zf.extractall(extract_dir)

    pyside6_dir = extract_dir / "PySide6"
    if not pyside6_dir.is_dir():
        log("ERROR: PySide6/ directory not found in extracted wheel")
        sys.exit(1)

    # ── Prune ─────────────────────────────────────────────────────────
    size_before = sum(f.stat().st_size for f in extract_dir.rglob("*") if f.is_file())
    log(f"Pruning  ({size_before / 1e6:.0f} MB before) ...")
    removed = prune_pyside6(pyside6_dir)
    size_after = sum(f.stat().st_size for f in extract_dir.rglob("*") if f.is_file())
    log(f"Removed {removed / 1e6:.0f} MB -> {size_after / 1e6:.0f} MB remaining")

    # ── Update metadata ───────────────────────────────────────────────
    log("Updating dist-info metadata...")
    dist_infos = list(extract_dir.glob("PySide6_Essentials-*.dist-info"))
    if not dist_infos:
        log("ERROR: dist-info directory not found in extracted wheel")
        sys.exit(1)
    essentials_di = dist_infos[0]
    pyside6_di = extract_dir / f"PySide6-{version}.dist-info"
    essentials_di.rename(pyside6_di)

    # Rename package in METADATA; keep only shiboken6 dependency
    metadata_path = pyside6_di / "METADATA"
    text = metadata_path.read_text(encoding="utf-8")
    text = re.sub(r"^Name: PySide6_Essentials$", "Name: PySide6", text, flags=re.MULTILINE)
    lines = text.splitlines(keepends=True)
    lines = [
        ln for ln in lines
        if not re.match(r"Requires-Dist:", ln) or re.match(r"Requires-Dist:\s*shiboken6", ln)
    ]
    metadata_path.write_text("".join(lines), encoding="utf-8")

    # Update top_level.txt
    (pyside6_di / "top_level.txt").write_text("PySide6\n", encoding="utf-8")

    # Remove RECORD — wheel pack will regenerate it with correct hashes
    record = pyside6_di / "RECORD"
    if record.exists():
        record.unlink()

    # ── Pack ──────────────────────────────────────────────────────────
    log("Packing slim wheel...")
    run([str(python_exe), "-m", "wheel", "pack",
         str(extract_dir), "--dest-dir", str(dist_dir)])

    result_wheels = list(dist_dir.glob("PySide6-*.whl"))
    if result_wheels:
        w = result_wheels[0]
        log(f"Created: {w.name}  ({w.stat().st_size / 1e6:.1f} MB)")

    log(f"Done! Artifacts in: {dist_dir}")


if __name__ == "__main__":
    main()
