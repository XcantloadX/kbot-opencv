#!/usr/bin/env python3
"""
Build minimal opencv-python wheels with only core, imgproc, imgcodecs modules.
"""

import os
import sys
import subprocess
import shutil
import platform
import hashlib
import zipfile
from pathlib import Path

SYSTEM = platform.system()
MACHINE = platform.machine()


def log(msg):
    print(f"[build] {msg}", flush=True)


def run(cmd, **kwargs):
    log(f"+ {cmd if isinstance(cmd, str) else subprocess.list2cmdline(cmd)}")
    subprocess.check_call(cmd, **kwargs)


def main():
    python_exe = Path(sys.executable).resolve()
    opencv_version = os.environ.get("OPENCV_VERSION", "4.10.0")
    root = Path.cwd()
    src_dir = root / "opencv_src"
    build_dir = root / "opencv_build"
    install_dir = root / "opencv_install"
    dist_dir = root / "dist"
    wheel_staging = root / "wheel_staging"

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

    # ---- CMake Configure ----
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    _contrib_path = src_dir / "opencv_contrib" / "modules"

    cmake_flags = [
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
    nproc = os.cpu_count() or 4
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


def package_wheel(install_dir, staging, dist_dir, version, python_exe):
    if staging.exists():
        shutil.rmtree(staging)

    # Find cv2 Python module
    cv2_src = find_cv2_module(install_dir)
    if not cv2_src:
        log("ERROR: cv2 Python module not found after install!")
        sys.exit(1)
    log(f"Found cv2 module at: {cv2_src}")

    # Determine wheel tag
    tag = get_wheel_tag(python_exe)
    log(f"Wheel tag: {tag}")

    # Build the wheel structure
    pkg_name = "cv2"
    dist_name = "opencv-python"
    dist_name_norm = dist_name.replace("-", "_")

    pkg_dir = staging / pkg_name
    dist_info = staging / f"{dist_name_norm}-{version}.dist-info"
    pkg_dir.mkdir(parents=True)
    dist_info.mkdir(parents=True)

    # Copy cv2 module files
    for item in cv2_src.iterdir():
        dest = pkg_dir / item.name
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, dest)

    # Fix config files: replace hardcoded build paths with relative paths
    fix_config_files(pkg_dir, version)

    # Copy OpenCV shared libraries into the cv2 package dir
    copied_libs = copy_opencv_libs(install_dir, pkg_dir)
    log(f"Bundled {len(copied_libs)} shared library files")

    # Write METADATA
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\n"
        f"Name: {dist_name}\n"
        f"Version: {version}\n"
        f"Summary: Minimal OpenCV Python bindings (core+imgproc+imgcodecs)\n"
        f"Requires-Python: >=3.8\n"
        f"Requires-Dist: numpy\n"
    )

    # Write WHEEL
    (dist_info / "WHEEL").write_text(
        "Wheel-Version: 1.0\n"
        "Generator: kbot-opencv build script\n"
        "Root-Is-Purelib: false\n"
        f"Tag: {tag}\n"
    )

    # Write top_level.txt
    (dist_info / "top_level.txt").write_text("cv2\n")

    # Write entry_points.txt if needed (not strictly necessary)
    # Create RECORD
    records = []
    for file_path in sorted(staging.rglob("*")):
        if file_path.is_file():
            arcname = str(file_path.relative_to(staging))
            h = hashlib.sha256(file_path.read_bytes()).hexdigest()
            sz = file_path.stat().st_size
            records.append(f"{arcname},sha256={h},{sz}")
    records.append(f"{dist_name_norm}-{version}.dist-info/RECORD,,")
    (dist_info / "RECORD").write_text("\n".join(records) + "\n")

    # Create .whl file
    os.makedirs(dist_dir, exist_ok=True)
    wheel_name = f"{dist_name_norm}-{version}-{tag}.whl"
    wheel_path = dist_dir / wheel_name
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in staging.rglob("*"):
            if file_path.is_file():
                arcname = str(file_path.relative_to(staging))
                zf.write(file_path, arcname)

    log(f"Created wheel: {wheel_path} ({wheel_path.stat().st_size / 1024 / 1024:.1f} MB)")


def fix_config_files(pkg_dir, version):
    """Replace hardcoded build paths with LOADER_DIR-relative paths."""
    py_ver = f"python-{sys.version_info.major}.{sys.version_info.minor}"

    # Fix config.py (BINARIES_PATHS)
    config_py = pkg_dir / "config.py"
    config_py.write_text(
        "import os\n"
        "BINARIES_PATHS = [LOADER_DIR] + BINARIES_PATHS\n"
    )
    log(f"Fixed config.py")

    # Fix config-3.xx.py (PYTHON_EXTENSIONS_PATHS)
    config_ver = pkg_dir / f"config-{sys.version_info.major}.{sys.version_info.minor}.py"
    if config_ver.exists():
        config_ver.write_text(
            "PYTHON_EXTENSIONS_PATHS = [os.path.join(LOADER_DIR, '{}')] + PYTHON_EXTENSIONS_PATHS\n".format(py_ver)
        )
        log(f"Fixed {config_ver.name}")


def find_cv2_module(install_dir):
    patterns = [
        "lib/python*/site-packages/cv2",
        "lib/python*/cv2",
        "python/cv2",
        "Lib/site-packages/cv2",
    ]
    for pattern in patterns:
        for match in install_dir.glob(pattern):
            if match.is_dir():
                return match
    # Fallback: search broadly in install_dir
    for cv2_dir in install_dir.rglob("cv2"):
        if cv2_dir.is_dir() and (cv2_dir / "__init__.py").exists():
            return cv2_dir
    # Fallback: search in the running Python's site-packages
    # (cmake --install may install directly to system site-packages)
    import site
    for sp in site.getsitepackages():
        cv2_sp = Path(sp) / "cv2"
        if cv2_sp.is_dir():
            return cv2_sp
    return None


def copy_opencv_libs(install_dir, dst_dir):
    copied = []
    if SYSTEM == "Windows":
        for dll in install_dir.rglob("*.dll"):
            if "opencv" in dll.name.lower():
                shutil.copy2(dll, dst_dir / dll.name)
                copied.append(dll.name)
        # Also copy any zlib, png, jpeg DLLs
        for dll in install_dir.rglob("*.dll"):
            name_lower = dll.name.lower()
            if any(x in name_lower for x in ["zlib", "libpng", "libjpeg", "libtiff"]):
                if dll.name not in copied:
                    shutil.copy2(dll, dst_dir / dll.name)
                    copied.append(dll.name)
    else:
        ext = "*.dylib*" if SYSTEM == "Darwin" else "*.so*"
        for lib in install_dir.rglob(ext):
            name = lib.name
            # Handle symlinks on Linux/macOS
            if lib.is_symlink():
                continue
            if "opencv" in name.lower():
                # On Linux, we need the actual file (not symlink)
                # and we set rpath to point to the wheel dir
                dest = dst_dir / name
                shutil.copy2(lib, dest)
                copied.append(name)
    return copied


def get_wheel_tag(python_exe):
    """Get wheel tag like cp312-cp312-win_amd64."""
    try:
        result = subprocess.run(
            [str(python_exe), "-c",
             "from wheel.bdist_wheel import get_tag; print('-'.join(get_tag()))"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        py_ver = f"cp{sys.version_info.major}{sys.version_info.minor}"
        if SYSTEM == "Windows":
            plat = "win_amd64" if MACHINE == "AMD64" else "win32"
        elif SYSTEM == "Darwin":
            plat = "macosx_11_0_arm64" if MACHINE == "arm64" else "macosx_11_0_x86_64"
        else:
            plat = "linux_x86_64" if MACHINE == "x86_64" else "linux_aarch64"
        return f"{py_ver}-{py_ver}-{plat}"


if __name__ == "__main__":
    main()
