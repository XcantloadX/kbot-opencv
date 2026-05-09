#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import site
import subprocess
import sys
import warnings
from pathlib import Path
from typing import NoReturn

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
    opencv_version: str = os.environ.get("OPENCV_VERSION", "4.10.0")
    root: Path = Path.cwd()
    src_dir: Path = root / "opencv_src"
    build_dir: Path = root / "opencv_build"
    install_dir: Path = root / "opencv_install"
    dist_dir: Path = root / "dist"
    wheel_staging: Path = root / "wheel_staging"

    log(f"Python: {python_exe}")
    log(f"OpenCV version: {opencv_version}")
    log(f"System: {SYSTEM} {MACHINE}")

    # ---- Clone OpenCV and contrib ----
    src_dir.mkdir(parents=True, exist_ok=True)
    if not (src_dir / "opencv").exists():
        run(["git", "clone", "--depth", "1", "--branch", opencv_version,
             "https://github.com/opencv/opencv.git"], cwd=src_dir)
    if not (src_dir / "opencv_contrib").exists():
        run(["git", "clone", "--depth", "1", "--branch", opencv_version,
             "https://github.com/opencv/opencv_contrib.git"], cwd=src_dir)

    # ---- Patch typing stubs generator to skip unresolvable types ----
    patch_file: Path = root / "opencv" / "typing_generator.patch"
    if patch_file.exists():
        log(f"Applying patch: {patch_file}")
        run(["git", "apply", str(patch_file)], cwd=src_dir / "opencv")
    else:
        log("WARN: typing_generator.patch not found, skipping")

    # ---- CMake Configure ----
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    cmake_flags: list[str] = [
        f"-DPYTHON3_EXECUTABLE={python_exe}",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_SHARED_LIBS=ON",
        "-DBUILD_TESTS=OFF",
        "-DBUILD_PERF_TESTS=OFF",
        "-DBUILD_EXAMPLES=OFF",
        "-DBUILD_opencv_core=ON",
        "-DBUILD_opencv_imgproc=ON",
        "-DBUILD_opencv_imgcodecs=ON",
        "-DBUILD_opencv_highgui=ON",
        "-DBUILD_opencv_videoio=OFF",
        "-DBUILD_opencv_dnn=OFF",
        "-DBUILD_opencv_stitching=OFF",
        "-DBUILD_opencv_calib3d=OFF",
        "-DBUILD_opencv_features2d=OFF",
        "-DBUILD_opencv_objdetect=OFF",
        "-DBUILD_opencv_ml=OFF",
        "-DBUILD_opencv_video=OFF",
        "-DBUILD_opencv_photo=OFF",
        "-DBUILD_opencv_flann=OFF",
        "-DBUILD_opencv_gapi=OFF",
        "-DBUILD_opencv_java_bindings_generator=OFF",
        "-DBUILD_opencv_python_bindings_generator=ON",
        "-DBUILD_opencv_python3=ON",
        "-DBUILD_opencv_js_bindings_generator=OFF",
        "-DBUILD_opencv_world=OFF",
        "-DWITH_FFMPEG=OFF",
        "-DWITH_GSTREAMER=OFF",
        "-DWITH_VTK=OFF",
        "-DWITH_GTK=OFF",
        "-DWITH_QT=OFF",
        "-DWITH_OPENCL=OFF",
        "-DWITH_OPENGL=OFF",
        "-DWITH_EIGEN=OFF",
        "-DWITH_JASPER=OFF",
        "-DWITH_WEBP=OFF",
        "-DWITH_TIFF=OFF",
        "-DWITH_OPENEXR=OFF",
        "-DWITH_1394=OFF",
        "-DWITH_PROTOBUF=OFF",
        "-DWITH_IPP=OFF",
        "-DBUILD_JPEG=ON",
        "-DBUILD_PNG=ON",
        "-DBUILD_ZLIB=ON",
    ]

    if SYSTEM == "Windows":
        cmake_flags += ["-DWITH_MSMF=OFF", "-DWITH_DIRECTX=OFF", "-DWITH_DSHOW=OFF"]

    log("Configuring with CMake...")
    run(["cmake", str(src_dir / "opencv")] + cmake_flags, cwd=build_dir)

    # ---- Build ----
    nproc: int = os.cpu_count() or 4
    log(f"Building (parallel={nproc})...")
    run(["cmake", "--build", ".", "--config", "Release", "--parallel", str(nproc)], cwd=build_dir)

    # ---- Install ----
    if install_dir.exists():
        shutil.rmtree(install_dir)
    log("Installing...")
    run(["cmake", "--install", ".", "--config", "Release", "--prefix", str(install_dir)], cwd=build_dir)

    # ---- Package wheel ----
    log("Packaging wheel...")
    package_wheel(install_dir, wheel_staging, dist_dir, opencv_version, python_exe)

    log(f"Done! Artifacts in: {dist_dir}")


def package_wheel(
    install_dir: Path,
    staging: Path,
    dist_dir: Path,
    version: str,
    python_exe: Path,
) -> None:
    if staging.exists():
        shutil.rmtree(staging)

    cv2_src: Path | None = find_cv2_module(install_dir)
    if not cv2_src:
        log("ERROR: cv2 Python module not found after install!")
        sys.exit(1)
    log(f"Found cv2 module at: {cv2_src}")

    tag: str = get_wheel_tag(python_exe)
    log(f"Wheel tag: {tag}")

    pkg_name: str = "cv2"
    dist_name: str = "opencv-python"
    dist_name_norm: str = dist_name.replace("-", "_")

    pkg_dir: Path = staging / pkg_name
    dist_info: Path = staging / f"{dist_name_norm}-{version}.dist-info"
    pkg_dir.mkdir(parents=True)
    dist_info.mkdir(parents=True)

    # Copy cv2 module files
    for item in cv2_src.iterdir():
        dest: Path = pkg_dir / item.name
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, dest)

    _clean_typing_module(pkg_dir)

    fix_config_files(pkg_dir)

    copied_libs: list[str] = copy_opencv_libs(install_dir, pkg_dir)
    log(f"Bundled {len(copied_libs)} shared library files")

    # Write minimal metadata – wheel pack will fill in RECORD etc.
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\n"
        f"Name: {dist_name}\n"
        f"Version: {version}\n"
        f"Summary: Wrapper package for OpenCV python bindings\n"
        f"Requires-Python: >=3.8\n"
        f"Requires-Dist: numpy\n"
    )

    (dist_info / "WHEEL").write_text(
        "Wheel-Version: 1.0\n"
        "Generator: kbot-opencv\n"
        "Root-Is-Purelib: false\n"
        f"Tag: {tag}\n"
    )

    (dist_info / "top_level.txt").write_text("cv2\n")

    # Use standard wheel pack instead of manual zip + RECORD
    os.makedirs(dist_dir, exist_ok=True)
    run([str(python_exe), "-m", "wheel", "pack", str(staging), "--dest-dir", str(dist_dir)])
    log(f"Created wheel in: {dist_dir}")


def _clean_typing_module(pkg_dir: Path) -> None:
    init_py: Path = pkg_dir / "typing" / "__init__.py"
    if not init_py.exists():
        return
    content: str = init_py.read_text(encoding="utf-8")
    for name in ["ExtractArgsCallback", "ExtractMetaCallback"]:
        content = content.replace(f'    "{name}",\n', "")
        content = __import__("re").sub(
            rf"^{name}\s*=.*\n?", "", content, flags=__import__("re").MULTILINE
        )
    content = __import__("re").sub(r'\n\s*\n([ ]*")', r"\n\1", content)
    init_py.write_text(content)


def fix_config_files(pkg_dir: Path) -> None:
    py_ver: str = f"python-{sys.version_info.major}.{sys.version_info.minor}"

    config_py: Path = pkg_dir / "config.py"
    config_py.write_text(
        "import os\n"
        "BINARIES_PATHS = [LOADER_DIR] + BINARIES_PATHS\n"
    )
    log("Fixed config.py")

    config_ver: Path = pkg_dir / f"config-{sys.version_info.major}.{sys.version_info.minor}.py"
    if config_ver.exists():
        config_ver.write_text(
            "PYTHON_EXTENSIONS_PATHS = [os.path.join(LOADER_DIR, '{}')] + PYTHON_EXTENSIONS_PATHS\n"
            .format(py_ver)
        )
        log(f"Fixed {config_ver.name}")


def find_cv2_module(install_dir: Path) -> Path | None:
    patterns: list[str] = [
        "lib/python*/site-packages/cv2",
        "lib/python*/cv2",
        "python/cv2",
        "Lib/site-packages/cv2",
    ]
    for pattern in patterns:
        for match in install_dir.glob(pattern):
            if match.is_dir():
                return match
    for cv2_dir in install_dir.rglob("cv2"):
        if cv2_dir.is_dir() and (cv2_dir / "__init__.py").exists():
            return cv2_dir
    for sp in site.getsitepackages():
        cv2_sp: Path = Path(sp) / "cv2"
        if cv2_sp.is_dir():
            return cv2_sp
    return None


def copy_opencv_libs(install_dir: Path, dst_dir: Path) -> list[str]:
    copied: list[str] = []
    if SYSTEM == "Windows":
        for dll in install_dir.rglob("*.dll"):
            if "opencv" in dll.name.lower():
                shutil.copy2(dll, dst_dir / dll.name)
                copied.append(dll.name)
        for dll in install_dir.rglob("*.dll"):
            name_lower: str = dll.name.lower()
            if any(x in name_lower for x in ["zlib", "libpng", "libjpeg"]):
                if dll.name not in copied:
                    shutil.copy2(dll, dst_dir / dll.name)
                    copied.append(dll.name)
    else:
        ext: str = "*.dylib*" if SYSTEM == "Darwin" else "*.so*"
        for lib in install_dir.rglob(ext):
            if lib.is_symlink():
                continue
            if "opencv" in lib.name.lower():
                shutil.copy2(lib, dst_dir / lib.name)
                copied.append(lib.name)
    return copied


def get_wheel_tag(python_exe: Path) -> str:
    try:
        result = subprocess.run(
            [str(python_exe), "-c",
             "from wheel.bdist_wheel import get_tag; print('-'.join(get_tag()))"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except Exception:
        py_ver: str = f"cp{sys.version_info.major}{sys.version_info.minor}"
        if SYSTEM == "Windows":
            plat: str = "win_amd64" if MACHINE == "AMD64" else "win32"
        elif SYSTEM == "Darwin":
            plat = "macosx_11_0_arm64" if MACHINE == "arm64" else "macosx_11_0_x86_64"
        else:
            plat = "linux_x86_64" if MACHINE == "x86_64" else "linux_aarch64"
        return f"{py_ver}-{py_ver}-{plat}"


if __name__ == "__main__":
    main()
