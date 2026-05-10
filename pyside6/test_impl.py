#!/usr/bin/env python3
"""Functional tests for the slimmed PySide6 wheel.

Verifies that each retained Qt module is importable and exposes expected
classes. Intentionally avoids creating QApplication / QCoreApplication so
the suite runs safely in headless CI environments.
"""
from __future__ import annotations

import sys

_PASS = "\033[32mPASS\033[0m"
_FAIL = "\033[31mFAIL\033[0m"
_failures: list[str] = []
_passes: int = 0


def check(name: str, fn) -> None:
    global _passes
    try:
        fn()
        print(f"  {_PASS} {name}")
        _passes += 1
    except Exception as exc:
        print(f"  {_FAIL} {name}: {exc}")
        _failures.append(name)


def _assert(cond: bool, msg: str = "") -> None:
    if not cond:
        raise AssertionError(msg or "assertion failed")


# ── Per-module test functions ──────────────────────────────────────────────

def test_qtcore() -> None:
    print("QtCore:")
    from PySide6 import QtCore
    check("module import",         lambda: _assert(hasattr(QtCore, "QCoreApplication")))
    check("QTimer class",          lambda: _assert(QtCore.QTimer is not None))
    check("QThread class",         lambda: _assert(QtCore.QThread is not None))
    check("Qt.AlignLeft flag",     lambda: _assert(int(QtCore.Qt.AlignLeft) >= 0))
    check("QPoint arithmetic",     lambda: _assert(QtCore.QPoint(3, 4) + QtCore.QPoint(1, 1) == QtCore.QPoint(4, 5)))
    check("QSize constructor",     lambda: _assert(QtCore.QSize(1920, 1080).width() == 1920))
    check("QByteArray",            lambda: _assert(QtCore.QByteArray(b"hello").size() == 5))
    check("QRect",                 lambda: _assert(QtCore.QRect(0, 0, 100, 200).width() == 100))


def test_qtgui() -> None:
    print("QtGui:")
    from PySide6 import QtGui
    check("module import",         lambda: _assert(hasattr(QtGui, "QColor")))
    check("QColor by name",        lambda: _assert(QtGui.QColor("red").red() == 255))
    check("QColor components",     lambda: _assert(QtGui.QColor(0, 128, 255).green() == 128))
    check("QImage create",         lambda: _assert(not QtGui.QImage(64, 64, QtGui.QImage.Format.Format_RGB32).isNull()))
    check("QFont",                 lambda: _assert(isinstance(QtGui.QFont("Arial").family(), str)))
    check("QPixmap class",         lambda: _assert(QtGui.QPixmap is not None))


def test_qtwidgets() -> None:
    print("QtWidgets:")
    from PySide6 import QtWidgets
    check("module import",         lambda: _assert(hasattr(QtWidgets, "QApplication")))
    check("QApplication class",    lambda: _assert(QtWidgets.QApplication is not None))
    check("QWidget class",         lambda: _assert(QtWidgets.QWidget is not None))
    check("QLabel class",          lambda: _assert(QtWidgets.QLabel is not None))
    check("QPushButton class",     lambda: _assert(QtWidgets.QPushButton is not None))
    check("QMainWindow class",     lambda: _assert(QtWidgets.QMainWindow is not None))


def test_qtqml() -> None:
    print("QtQml:")
    from PySide6 import QtQml
    check("module import",         lambda: _assert(hasattr(QtQml, "QQmlEngine")))
    check("QQmlEngine class",      lambda: _assert(QtQml.QQmlEngine is not None))
    check("QQmlComponent class",   lambda: _assert(QtQml.QQmlComponent is not None))
    check("QJSEngine class",       lambda: _assert(QtQml.QJSEngine is not None))


def test_qtquick() -> None:
    print("QtQuick:")
    from PySide6 import QtQuick
    check("module import",         lambda: _assert(hasattr(QtQuick, "QQuickView")))
    check("QQuickView class",      lambda: _assert(QtQuick.QQuickView is not None))
    check("QQuickItem class",      lambda: _assert(QtQuick.QQuickItem is not None))


def test_qtquickcontrols2() -> None:
    print("QtQuickControls2:")
    from PySide6 import QtQuickControls2
    check("module import",         lambda: _assert(hasattr(QtQuickControls2, "QQuickStyle")))
    check("QQuickStyle class",     lambda: _assert(QtQuickControls2.QQuickStyle is not None))


def test_qtsvg() -> None:
    print("QtSvg:")
    from PySide6 import QtSvg
    check("module import",         lambda: _assert(hasattr(QtSvg, "QSvgRenderer")))
    check("QSvgRenderer class",    lambda: _assert(QtSvg.QSvgRenderer is not None))
    check("QSvgGenerator class",   lambda: _assert(QtSvg.QSvgGenerator is not None))


# ── Entry point ────────────────────────────────────────────────────────────

_SUITES = [
    test_qtcore,
    test_qtgui,
    test_qtwidgets,
    test_qtqml,
    test_qtquick,
    test_qtquickcontrols2,
    test_qtsvg,
]


def main() -> None:
    print(f"Python  {sys.version}")
    import PySide6
    print(f"PySide6 {PySide6.__version__}")
    print()

    for suite in _SUITES:
        suite()

    print()
    total = _passes + len(_failures)
    if _failures:
        print(f"FAILED  {len(_failures)}/{total}  —  {', '.join(_failures)}")
        sys.exit(1)
    print(f"All {total} checks passed.")


if __name__ == "__main__":
    main()
