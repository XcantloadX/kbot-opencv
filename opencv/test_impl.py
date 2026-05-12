#!/usr/bin/env python3
"""Run OpenCV correctness checks for core, imgproc, imgcodecs, highgui."""

import cv2
import numpy as np
import os
import platform
import sys
import tempfile

print(f"OpenCV version: {cv2.__version__}")
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Install path: {cv2.__file__}")


def check_core():
    print("\n--- core ---")
    m = np.zeros((100, 100, 3), dtype=np.uint8)
    print(f"Mat shape: {m.shape}, dtype: {m.dtype}, size: {m.size}")

    s = (10, 20, 30, 255)
    print(f"Scalar: {s}")

    p = (42, 99)
    print(f"Point: {p}")

    size = (640, 480)
    print(f"Size: {size}")

    rect = (10, 20, 200, 150)
    print(f"Rect: {rect}, area: {rect[2] * rect[3]}")

    # LUT
    lut = np.arange(256, dtype=np.uint8)
    img = np.array([0, 128, 255], dtype=np.uint8).reshape(1, 3)
    result = cv2.LUT(img, lut)
    assert np.array_equal(result[0], [0, 128, 255]), "LUT failed"
    print("LUT OK")

    # split / merge
    b, g, r = cv2.split(m)
    merged = cv2.merge([b, g, r])
    print(f"split/merge shape: {merged.shape}")

    # flip
    flipped = cv2.flip(m, 1)
    print(f"flip OK: {flipped.shape}")

    # transpose
    t = cv2.transpose(m)
    print(f"transpose OK: {t.shape}")

    # convert
    f32 = m.astype(np.float32)
    conv = cv2.convertScaleAbs(f32)
    print(f"convertScaleAbs OK: {conv.shape}")

    # addWeighted
    a = cv2.addWeighted(m, 0.5, m, 0.5, 0)
    print(f"addWeighted OK: {a.shape}")

    # minMaxLoc / meanStdDev
    gray = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
    min_v, max_v, min_loc, max_loc = cv2.minMaxLoc(gray)
    print(f"minMaxLoc: min={min_v}@{min_loc}, max={max_v}@{max_loc}")

    mean, std = cv2.meanStdDev(gray)
    print(f"meanStdDev: mean={mean[0][0]:.2f}, std={std[0][0]:.2f}")

    # norm
    n = cv2.norm(gray, cv2.NORM_L2)
    print(f"norm L2: {n:.2f}")

    # border
    bordered = cv2.copyMakeBorder(gray, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=255)
    print(f"copyMakeBorder OK: {bordered.shape}")


def check_imgproc():
    print("\n--- imgproc ---")
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print(f"cvtColor OK: {gray.shape}")

    # Filter
    blurred = cv2.GaussianBlur(gray, (5, 5), 1.5)
    print(f"GaussianBlur OK: {blurred.shape}")

    median = cv2.medianBlur(gray, 5)
    print(f"medianBlur OK: {median.shape}")

    bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
    print(f"bilateralFilter OK: {bilateral.shape}")

    # Morphology
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    eroded = cv2.erode(gray, kernel)
    dilated = cv2.dilate(gray, kernel)
    opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    print(f"morphology OK: erode={eroded.shape}, dilate={dilated.shape}")

    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    print(f"Canny OK: {edges.shape}")

    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1)
    print(f"Sobel OK: dx={sobel_x.shape}, dy={sobel_y.shape}")

    # Geometric transforms
    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), 45, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h))
    print(f"warpAffine (rotate) OK: {rotated.shape}")

    resized = cv2.resize(gray, (50, 50))
    print(f"resize OK: {resized.shape}")

    # Threshold
    _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    print(f"threshold OK: {thresh.shape}")

    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 2)
    print(f"adaptiveThreshold OK: {adaptive.shape}")

    # Histogram
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    print(f"calcHist OK: len={len(hist)}, total={hist.sum():.0f}")

    equalized = cv2.equalizeHist(gray)
    print(f"equalizeHist OK: {equalized.shape}")

    # Contour detection
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    print(f"findContours OK: {len(contours)} contours found")

    if contours:
        c = contours[0]
        area = cv2.contourArea(c)
        length = cv2.arcLength(c, True)
        print(f"contour #0: area={area:.1f}, length={length:.1f}")

    # Hough
    edges_for_hough = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges_for_hough, 1, np.pi / 180, 50)
    print(f"HoughLinesP OK: {len(lines) if lines is not None else 0} lines")

    # Drawing
    canvas = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.line(canvas, (10, 10), (190, 190), (0, 255, 0), 2)
    cv2.circle(canvas, (100, 100), 50, (0, 0, 255), 2)
    cv2.rectangle(canvas, (20, 20), (180, 180), (255, 0, 0), 2)
    cv2.ellipse(canvas, (100, 100), (80, 40), 0, 0, 360, (255, 255, 0), 2)
    cv2.putText(canvas, "OpenCV", (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    print(f"drawing OK: {canvas.shape}")


def check_imgcodecs():
    print("\n--- imgcodecs ---")
    img = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
    tmpdir = tempfile.mkdtemp()

    # imwrite / imread
    path = os.path.join(tmpdir, "test.png")
    assert cv2.imwrite(path, img), "imwrite failed"
    loaded = cv2.imread(path)
    assert loaded is not None, "imread returned None"
    assert loaded.shape == (50, 50, 3), f"imread shape mismatch: {loaded.shape}"
    print(f"imwrite/imread (PNG) OK: {loaded.shape}")

    # JPEG
    path_jpg = os.path.join(tmpdir, "test.jpg")
    cv2.imwrite(path_jpg, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    loaded_jpg = cv2.imread(path_jpg)
    assert loaded_jpg is not None, "imread JPEG returned None"
    print(f"imwrite/imread (JPEG) OK: {loaded_jpg.shape}")

    # imencode / imdecode
    success, buf = cv2.imencode(".png", img)
    assert success, "imencode failed"
    print(f"imencode OK: buffer size={len(buf)} bytes")
    decoded = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    assert decoded is not None, "imdecode returned None"
    assert decoded.shape == (50, 50, 3), f"imdecode shape mismatch: {decoded.shape}"
    print(f"imdecode OK: {decoded.shape}")

    # imread grayscale
    gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    assert gray is not None and gray.ndim == 2, "IMREAD_GRAYSCALE failed"
    print(f"imread (grayscale) OK: {gray.shape}")

    # imread unchanged
    uc = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    assert uc is not None, "IMREAD_UNCHANGED failed"
    print(f"imread (unchanged) OK: {uc.shape}")

    os.remove(path)
    os.remove(path_jpg)
    os.rmdir(tmpdir)


def check_highgui():
    print("\n--- highgui ---")
    # No window display testing in headless CI,
    # but verify the module is importable and basic functions exist
    assert hasattr(cv2, "imshow"), "imshow not available"
    assert hasattr(cv2, "waitKey"), "waitKey not available"
    assert hasattr(cv2, "namedWindow"), "namedWindow not available"
    assert hasattr(cv2, "destroyAllWindows"), "destroyAllWindows not available"
    print("highgui API symbols present")


def check_watershed():
    """minimal watershed test that exercises the algorithm."""
    print("\n--- watershed ---")
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:80, 20:80] = (255, 255, 255)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    # distance transform
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    dist = np.uint8(dist)
    _, markers = cv2.connectedComponents(dist)
    markers = cv2.watershed(img, markers)
    print(f"watershed OK: markers shape={markers.shape}, max label={markers.max()}")


def check_grabcut():
    """minimal grabCut test."""
    print("\n--- grabcut ---")
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:80, 20:80] = (255, 255, 255)
    mask = np.zeros((100, 100), dtype=np.uint8)
    bgd = np.zeros((1, 65), dtype=np.float64)
    fgd = np.zeros((1, 65), dtype=np.float64)
    rect = (10, 10, 80, 80)
    cv2.grabCut(img, mask, rect, bgd, fgd, 1, cv2.GC_INIT_WITH_RECT)
    print(f"grabCut OK: mask unique values={np.unique(mask)}")


def check_remap():
    """test remap (geometric transform via mapping)."""
    print("\n--- remap ---")
    gray = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
    h, w = gray.shape
    map_x, map_y = np.meshgrid(np.arange(w), np.arange(h))
    map_x = map_x.astype(np.float32)
    map_y = map_y.astype(np.float32)
    remapped = cv2.remap(gray, map_x, map_y, cv2.INTER_LINEAR)
    assert np.array_equal(remapped, gray), "remap identity failed"
    print("remap OK")


def check_filter2d():
    """test filter2D."""
    print("\n--- filter2D ---")
    gray = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
    kernel = np.ones((3, 3), dtype=np.float32) / 9
    filtered = cv2.filter2D(gray, -1, kernel)
    print(f"filter2D OK: {filtered.shape}")


def check_pyrdown_pyrup():
    """test pyrDown / pyrUp."""
    print("\n--- pyrDown/pyrUp ---")
    gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    lower = cv2.pyrDown(gray)
    upper = cv2.pyrUp(lower)
    print(f"pyrDown OK: {lower.shape}, pyrUp OK: {upper.shape}")


if __name__ == "__main__":
    check_core()
    check_imgproc()
    check_imgcodecs()
    check_highgui()
    check_watershed()
    check_grabcut()
    check_remap()
    check_filter2d()
    check_pyrdown_pyrup()

    print("\n=== All tests PASSED ===")
