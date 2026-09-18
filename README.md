# 嘴唇闭合提醒器

一个完全本地运行的 Windows 摄像头工具。它使用 MediaPipe 面部关键点计算嘴唇开合比例，在用户完成个人校准后，识别持续张嘴状态并播放系统提示音。

> 本项目只能识别嘴唇是否持续张开，不能判断真实呼吸气流，不是医疗诊断工具。

## 功能

- 本地摄像头画面与嘴唇关键点预览。
- 闭嘴、轻微张嘴双点个人校准。
- 持续张嘴计时、页面红色提醒和 Windows 系统提示音。
- 通过嘴唇比例波动过滤一部分说话动作。
- 设置与校准保存在 `%LOCALAPPDATA%\MouthMonitor\config.json`。
- 暂停或停止后立即释放摄像头。
- 所有识别均在本机完成，不上传、不保存图片或视频。

## 环境要求

- Windows 10 或 Windows 11。
- Python 3.11 或 3.12。
- 可用摄像头。
- 推荐使用 [uv](https://docs.astral.sh/uv/) 管理依赖。

MediaPipe 的 Windows 依赖体积较大，首次安装前请确保系统盘有足够空间。

## 源码运行

```powershell
uv sync --group dev
uv run mouth-monitor
```

应用默认监听 `127.0.0.1:8765`，启动后自动打开浏览器。若不希望自动打开浏览器：

```powershell
$env:MOUTH_MONITOR_NO_BROWSER = "1"
uv run mouth-monitor
```

## 使用流程

1. 点击“扫描摄像头”，选择可用设备。
2. 点击“开始监控”，确认画面中能识别人脸和嘴唇关键点。
3. 自然闭合嘴唇，点击“采集闭嘴基线”，稳定保持约 3 秒。
4. 轻微张嘴，点击“采集轻微张嘴”，稳定保持约 3 秒。
5. 恢复正常使用电脑；持续张嘴超过设置时间后会触发提醒。

校准结果与摄像头绑定。更换摄像头、拍摄距离或角度明显变化后，建议重新校准。

## Windows 打包

```powershell
.\scripts\build.ps1
```

如果系统盘空间不足，可将构建产物放到其他磁盘：

```powershell
.\scripts\build.ps1 -OutputRoot D:\mouth-monitor-build
```

构建脚本运行测试后生成：

```text
dist\MouthMonitor\MouthMonitor.exe
dist\MouthMonitor-windows-x64.zip
```

项目使用 PyInstaller `onedir` 模式，避免每次启动重复解压模型和动态库。

## 技术结构

```text
src/mouth_monitor/
├── app.py            FastAPI、WebSocket 与 MJPEG 接口
├── engine.py         摄像头线程、校准、状态机和提醒编排
├── camera.py         摄像头扫描、打开与释放
├── vision.py         MediaPipe 推理和嘴唇比例计算
├── state_machine.py  持续张嘴状态机
├── storage.py        本地设置持久化
├── assets/           MediaPipe 模型
└── web/              浏览器控制台
```

## 隐私与限制

- 服务只监听本机回环地址，不暴露到局域网。
- 不保存摄像头图片、视频或完整面部关键点。
- “嘴唇张开”不等于“正在口呼吸”，鼻呼吸时也可能张嘴，闭嘴时也无法排除其他呼吸问题。
- 光线、遮挡、面部角度、说话、进食和摄像头位置都会影响识别结果。
- 如果长期无法自然闭合嘴唇或存在呼吸、睡眠问题，应咨询专业医生。

## 开发

```powershell
uv sync --group dev
uv run pytest -q
```

贡献说明见 `CONTRIBUTING.md`，项目采用 MIT License。
