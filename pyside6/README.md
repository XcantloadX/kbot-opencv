# PySide6 精简版

通过后处理方式对官方 `PySide6_Essentials` wheel 进行裁剪，仅保留 QtQuick/QML 桌面 UI 应用所需的最小模块集，重新打包为 `PySide6` wheel，可直接替换官方安装包。

## 保留的模块

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

## 保留的 QML 插件目录

`QtQml`、`QtQuick`（包含 Controls/Windows 与 Controls/Basic 样式）

## 保留的 Qt 插件目录

`generic`、`iconengines`、`imageformats`、`platforminputcontexts`、`platforms`、`renderers`、`styles`、`tls`

## 精简原理

与 OpenCV 不同，PySide6 采用**后处理**方式构建精简 wheel：

1. 从 PyPI 下载官方 `PySide6_Essentials` wheel
2. 解压后按保留列表删除不需要的 `.pyd`/`.so`、Qt 原生库、QML 目录、插件目录、翻译文件、存根文件等
3. 将 dist-info 元数据重命名为 `PySide6`，保留 `shiboken6` 依赖
4. 用 `wheel pack` 重新打包为标准 wheel

保留列表来源于 [ichikas-auto-assistant](https://github.com/XcantloadX/ichikas-auto-assistant) 项目中的 `tools/prune_pyside6.py`。

## 使用

```bash
# 手动触发构建（可自定义 PySide6 版本）
gh workflow run "Build & Test PySide6" -f pyside6_version=6.8.0

# 查看构建状态
gh run list --workflow pyside6_build.yml

# 下载构建产物
gh run download <run-id> --name pyside6-slim-<os>-<python-version>
```

### Python 示例

```python
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtQml import QQmlEngine
from PySide6.QtCore import QTimer, Qt

app = QApplication([])
label = QLabel("Hello, slim PySide6!")
label.show()
app.exec()
```

## 构建产物

| 平台 | 精简方式 |
|------|---------|
| Linux (x86_64) | 官方 manylinux_2_28 wheel 后处理裁剪 |
| Windows (x86_64) | 官方 win_amd64 wheel 后处理裁剪 |

构建完成后会自动发布到 GitHub Releases。
