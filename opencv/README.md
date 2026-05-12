# opencv-python 精简版

## 保留的模块

| 模块 | 说明 |
|------|------|
| `core` | 核心数据结构（Mat, Scalar, Point 等） |
| `imgproc` | 图像处理（滤波、形态学、几何变换、直方图等） |
| `imgcodecs` | 图像编解码（imread / imwrite / imencode / imdecode） |
| `highgui` | 图像显示（imshow / waitKey / namedWindow） |

所有其他 OpenCV 主模块及 contrib 模块均已关闭。

## 使用

```bash
# 手动触发构建
gh workflow run "Build & Test OpenCV"

# 查看构建状态
gh run list

# 下载构建产物
gh run download <run-id> --name opencv-wheel-<os>-<python-version>
```

构建完成后会自动发布到 GitHub Releases。
