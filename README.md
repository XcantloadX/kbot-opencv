# kbot-opencv

利用 GitHub Actions 编译精简版 Python 多媒体库 wheels，目前包含：

- **opencv-python**：仅保留图像处理核心模块
- **PyAV**：仅保留 H.264 解码能力

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
