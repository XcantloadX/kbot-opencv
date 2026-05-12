# PyAV 精简版（H.264 解码）

基于自定义编译的 FFmpeg，只保留 H.264 解码所需的最小组件集，wheel 内已打包全部 FFmpeg 共享库，无需额外安装。

## 保留的 FFmpeg 组件

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

## 使用

```bash
# 手动触发构建（可自定义 FFmpeg / PyAV 版本）
gh workflow run "Build & Test PyAV"

# 下载构建产物
gh run download <run-id> --name pyav-wheel-<os>-<python-version>
```

### Python 示例

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

## 构建产物

| 平台 | 编译工具链 |
|------|-----------|
| Linux (x86_64) | gcc + auditwheel（.so 打包进 wheel） |
| Windows (x86_64) | MSVC + delvewheel（.dll 打包进 wheel） |

构建完成后会自动发布到 GitHub Releases。
