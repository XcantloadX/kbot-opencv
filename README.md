# kbot-opencv

利用 GitHub Actions 编译精简版 Python 多媒体库 wheels。

| 项目             | 说明                                       |
| ---------------- | ------------------------------------------ |
| [opencv](opencv/)   | 仅保留图像处理核心模块                     |
| [numpy1](numpy1/)   | 无 OpenBLAS 依赖的 NumPy 1.x               |
| [pyav](pyav/)       | 仅保留 H.264 解码能力                      |
| [pyside6](pyside6/) | 仅保留 Qt Quick/QML 桌面 UI 所需的核心模块 |

每个子目录下有对应的 `README.md` 与构建脚本，Workflow 文件位于 `.github/workflows/`。
