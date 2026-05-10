# kbot-opencv

利用 GitHub Actions 编译精简版 Python 多媒体库 wheels，目前包含：

- **opencv-python**：仅保留图像处理核心模块
- **PyAV**：仅保留 H.264 解码能力
- **PySide6**：仅保留 Qt Quick/QML 桌面 UI 所需的核心模块

---

## opencv-python 精简版

### 保留的模块

| 模块 | 说明 |
|------|------|
| `core` | 核心数据结构（Mat, Scalar, Point 等） |
| `imgproc` | 图像处理（滤波、形态学、几何变换、直方图等） |
| `imgcodecs` | 图像编解码（imread / imwrite / imencode / imdecode） |
| `highgui` | 图像显示（imshow / waitKey / namedWindow） |

所有其他 OpenCV 主模块及 contrib 模块均已关闭。

### 使用

```bash
# 手动触发构建
gh workflow run "Build & Test OpenCV Wheels"

# 查看构建状态
gh run list

# 下载构建产物
gh run download <run-id> --name opencv-wheel-<os>-<python-version>
```

构建完成后会自动发布到 GitHub Releases。

---

## PyAV 精简版（H.264 解码）

基于自定义编译的 FFmpeg，只保留 H.264 解码所需的最小组件集，wheel 内已打包全部 FFmpeg 共享库，无需额外安装。

### 保留的 FFmpeg 组件

| 组件 | 说明 |
|------|------|
| `avcodec` | 编解码框架 |
| `avformat` | 容器格式框架（空壳，无 demuxer/muxer） |
| `avdevice` | 设备框架（空壳） |
| `avutil` | 基础工具库 |
| `avfilter` | 滤镜框架（空壳） |
| `swscale` | 像素格式转换 |
| `swresample` | 音频重采样框架（空壳） |
| Decoder | `h264` |
| Parser | `h264` |
| BSF | `h264_mp4toannexb` |

所有编码器、复用器、解复用器、协议、设备、滤镜、硬件加速均已禁用。

### 使用

```bash
# 手动触发构建（可自定义 FFmpeg / PyAV 版本）
gh workflow run "Build & Test PyAV Wheels"

# 下载构建产物
gh run download <run-id> --name pyav-wheel-<os>-<python-version>
```

#### Python 示例

```python
import av

# 创建 H.264 解码上下文
ctx = av.codec.CodecContext.create("h264", "r")

# 解码 Annex-B 裸流数据包
packet = av.Packet(annexb_bytes)
frames = ctx.decode(packet)

# swscale：YUV → RGB 转换
frame_rgb = frames[0].reformat(format="rgb24")
```

### 构建产物

| 平台 | 编译工具链 |
|------|-----------|
| Linux (x86_64) | gcc + auditwheel（.so 打包进 wheel） |
| Windows (x86_64) | MSVC + delvewheel（.dll 打包进 wheel） |

构建完成后会自动发布到 GitHub Releases。

---

## PySide6 精简版

通过后处理方式对官方 `PySide6_Essentials` wheel 进行裁剪，仅保留 QtQuick/QML 桌面 UI 应用所需的最小模块集，重新打包为 `PySide6` wheel，可直接替换官方安装包。

### 保留的模块

| 模块 | 说明 |
|------|------|
| `QtCore` | 核心类型（QTimer、QThread、Qt flags 等） |
| `QtGui` | GUI 基础（QColor、QImage、QFont、QPixmap 等） |
| `QtWidgets` | 传统部件（QApplication、QWidget、QLabel 等） |
| `QtQml` | QML 引擎（QQmlEngine、QJSEngine 等） |
| `QtQuick` | Quick 渲染（QQuickView、QQuickItem 等） |
| `QtQuickControls2` | Quick Controls 2 样式（Windows + Basic） |
| `QtSvg` | SVG 渲染（QSvgRenderer、QSvgGenerator） |

所有其他模块（QtWebEngine、Qt3D、QtMultimedia、QtOpenGL、QtNetwork 等）均已移除。

### 保留的 QML 插件目录

`QtQml`、`QtQuick`（包含 Controls/Windows 与 Controls/Basic 样式）

### 保留的 Qt 插件目录

`generic`、`iconengines`、`imageformats`、`platforminputcontexts`、`platforms`、`renderers`、`styles`、`tls`

### 精简原理

与 OpenCV 不同，PySide6 采用**后处理**方式构建精简 wheel：

1. 从 PyPI 下载官方 `PySide6_Essentials` wheel
2. 解压后按保留列表删除不需要的 `.pyd`/`.so`、Qt 原生库、QML 目录、插件目录、翻译文件、存根文件等
3. 将 dist-info 元数据重命名为 `PySide6`，保留 `shiboken6` 依赖
4. 用 `wheel pack` 重新打包为标准 wheel

保留列表来源于 [ichikas-auto-assistant](https://github.com/XcantloadX/ichikas-auto-assistant) 项目中的 `tools/prune_pyside6.py`。

### 使用

```bash
# 手动触发构建（可自定义 PySide6 版本）
gh workflow run "Build & Test PySide6 Slim Wheels" -f pyside6_version=6.8.0

# 查看构建状态
gh run list --workflow pyside6_build.yml

# 下载构建产物
gh run download <run-id> --name pyside6-slim-<os>-<python-version>
```

#### Python 示例

```python
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtQml import QQmlEngine
from PySide6.QtCore import QTimer, Qt

app = QApplication([])
label = QLabel("Hello, slim PySide6!")
label.show()
app.exec()
```

### 构建产物

| 平台 | 精简方式 |
|------|---------|
| Linux (x86_64) | 官方 manylinux_2_28 wheel 后处理裁剪 |
| Windows (x86_64) | 官方 win_amd64 wheel 后处理裁剪 |

构建完成后会自动发布到 GitHub Releases。
