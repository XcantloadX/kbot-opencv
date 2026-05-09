#!/usr/bin/env python3
"""Run NumPy correctness and OpenBLAS-absence checks."""

import numpy as np
import os
import platform
import sys

print(f"NumPy version: {np.__version__}")
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Install path: {np.__file__}")

np.show_config()

np_dir = os.path.dirname(np.__file__)
has_openblas = False
for root, dirs, files in os.walk(np_dir):
    for f in files:
        if 'openblas' in f.lower():
            has_openblas = True
            print(f"WARNING: OpenBLAS file found: {os.path.join(root, f)}")
            break
    if has_openblas:
        break

if has_openblas:
    print("FAIL: external BLAS found!")
    sys.exit(1)

print("OK: no external BLAS")

a = np.array([1, 2, 3, 4, 5])
b = np.array([10, 20, 30, 40, 50])
print(f"a + b = {a + b}")
print(f"dot = {np.dot(a, b)}")
print(f"a @ a = {a @ a}")

m1 = np.random.rand(100, 100)
m2 = np.random.rand(100, 100)
r = m1 @ m2
print(f"matmul 100x100: {r.shape}")

from numpy.linalg import inv, eig, det
mat = np.array([[4., 7.], [2., 6.]])
print(f"inv = {inv(mat)}")
print(f"det = {det(mat)}")
print(f"eigvals = {eig(mat)[0]}")

from numpy.fft import fft
print(f"fft = {fft(a)}")

print("\n=== All tests PASSED ===")
