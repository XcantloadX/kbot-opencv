# NumPy 精简版（无 OpenBLAS）

从源码编译 NumPy，**不链接 OpenBLAS**，生成的 wheel 不依赖任何外部 BLAS 库。

## 使用

```bash
# 手动触发构建（可自定义 NumPy 版本）
gh workflow run "Build & Test NumPy" -f numpy_version=1.26.4

# 下载构建产物
gh run download <run-id> --name numpy-wheel-<os>-<python-version>
```

构建完成后会自动发布到 GitHub Releases。
