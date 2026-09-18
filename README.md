# Mouth Monitor

> 本地、可校准、隐私优先的 Windows 嘴唇闭合提醒工具。

[![Windows Build](https://github.com/AdS4TN/mouth-monitor/actions/workflows/build-windows.yml/badge.svg)](https://github.com/AdS4TN/mouth-monitor/actions/workflows/build-windows.yml)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)
![Local First](https://img.shields.io/badge/processing-100%25%20local-16803a)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Mouth Monitor 是一款面向电脑用户的**嘴唇闭合习惯提醒工具**。它使用普通摄像头实时观察嘴唇开合状态，当检测到嘴唇持续张开时，通过页面高亮和 Windows 提示音提醒用户调整状态。

整个体验很简单：打开应用、完成一次个人校准，然后像平时一样工作或学习。Mouth Monitor 会在后台持续分析摄像头画面，并在无意识张嘴持续发生时及时提醒。

![Mouth Monitor 控制台](docs/screenshot.png)

## 它如何工作

```mermaid
flowchart LR
    Camera["本机摄像头"] --> Landmarks["MediaPipe 面部关键点"]
    Landmarks --> Ratio["计算嘴唇纵横开合比例"]
    Calibration["个人双点校准"] --> Thresholds["个人进入与退出阈值"]
    Ratio --> State["平滑、说话过滤与持续时间状态机"]
    Thresholds --> State
    State -->|"持续张开"| Reminder["页面变红 + Windows 提示音"]
    State -->|"恢复闭合"| Reset["清除计时并等待下一次"]
```

- 摄像头画面在当前电脑内存中实时处理。
- 应用打开后即可使用，识别过程完全在本地完成。
- 本地配置文件仅记录应用设置和个人校准数值。
- 暂停或停止监控时，应用会立即释放摄像头。

## 适用场景

- 工作或学习时经常无意识张嘴，希望得到轻量提醒；
- 想验证个人校准后的视觉识别是否对自己有效；
- 希望摄像头数据完全留在本机；
- 想研究 MediaPipe、本地视觉状态机或 Python 桌面工具架构。

## 快速开始

### 环境要求

- Windows 10 或 Windows 11；
- Python 3.11 或 3.12；
- 可用的内置或 USB 摄像头；
- 推荐使用 [uv](https://docs.astral.sh/uv/) 管理依赖。

MediaPipe 的 Windows 依赖体积较大，首次安装前请确保磁盘有足够空间。

### 从源码运行

```powershell
git clone https://github.com/AdS4TN/mouth-monitor.git
cd mouth-monitor
uv sync --group dev
uv run mouth-monitor
```

应用默认监听 `127.0.0.1:8765`，启动后自动打开浏览器。若不希望自动打开浏览器：

```powershell
$env:MOUTH_MONITOR_NO_BROWSER = "1"
uv run mouth-monitor
```

## 第一次使用

1. 点击“扫描摄像头”，选择可用设备；
2. 点击“开始监控”，确认画面中能识别人脸和嘴唇关键点；
3. 自然闭合嘴唇，点击“采集闭嘴基线”，稳定保持约 3 秒；
4. 轻微张嘴，点击“采集轻微张嘴”，稳定保持约 3 秒；
5. 恢复正常使用电脑，持续张嘴超过设置时间后会触发提醒。

校准结果与摄像头绑定。更换摄像头、拍摄距离或角度明显变化后，建议重新校准。

## 后端技术栈

| 技术 | 用途 |
| --- | --- |
| Python 3.11 / 3.12 | 核心运行环境 |
| FastAPI | 本地 HTTP API、控制接口和页面服务 |
| Uvicorn | 启动本地 ASGI 服务 |
| MediaPipe Face Landmarker | 提取面部与嘴唇关键点 |
| OpenCV | 摄像头采集、画面处理和 MJPEG 输出 |
| NumPy | 图像数据与数值计算 |
| WebSocket | 向控制台实时推送识别状态 |
| JSON | 持久化用户设置与校准数据 |
| winsound | 播放 Windows 系统提示音 |
| PyInstaller | 构建可双击运行的 Windows 程序 |

后端以后台线程持续读取摄像头画面，视觉模块生成嘴唇状态数据，状态机完成持续时间判断，再通过 FastAPI 和 WebSocket 将结果同步到浏览器控制台。

## Windows 打包

```powershell
.\scripts\build.ps1
```

如果系统盘空间不足，可将构建环境和产物放到其他磁盘：

```powershell
$env:UV_CACHE_DIR = "D:\mouth-monitor-build\cache"
$env:UV_PROJECT_ENVIRONMENT = "D:\mouth-monitor-build\venv"
$env:TEMP = "D:\mouth-monitor-build\temp"
$env:TMP = "D:\mouth-monitor-build\temp"
.\scripts\build.ps1 -OutputRoot D:\mouth-monitor-build\release
```

构建脚本会先执行测试，然后生成：

```text
dist\MouthMonitor\MouthMonitor.exe
dist\MouthMonitor-windows-x64.zip
```

项目使用 PyInstaller `onedir` 模式，避免每次启动重复解压模型和动态库。

## 项目结构

```text
src/mouth_monitor/
├── app.py            FastAPI、WebSocket 与 MJPEG 接口
├── engine.py         摄像头线程、校准、状态机和提醒编排
├── camera.py         摄像头扫描、打开与释放
├── vision.py         MediaPipe 推理和嘴唇比例计算
├── state_machine.py  持续张嘴状态机
├── calibration.py    双点校准与阈值生成
├── storage.py        本地设置持久化
├── reminder.py       Windows 系统提示音与冷却
├── assets/           MediaPipe 模型
└── web/              浏览器控制台
```

核心模块刻意分离：视觉层只负责产生嘴唇比例，状态机不依赖摄像头和 MediaPipe，因此可以用普通数值输入完成自动测试。

## 开发与测试

```powershell
uv sync --group dev
uv run pytest -q
```

当前测试覆盖：

- 双点校准与失败条件；
- 闭嘴、嘴部活动、持续张嘴状态转换；
- 摄像头切换后校准失效；
- 设置保存、读取和损坏恢复；
- FastAPI 页面、状态、启动和设置接口。

## License

[MIT](LICENSE) © 2026 Mouth Monitor Contributors
