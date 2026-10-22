# 语音输入工具 · VoiceInputTool

[![CI](https://github.com/XIA1249218726/voice-input-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/XIA1249218726/voice-input-tool/actions/workflows/ci.yml)
[![Release](https://github.com/XIA1249218726/voice-input-tool/actions/workflows/release.yml/badge.svg)](https://github.com/XIA1249218726/voice-input-tool/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20x64-blue)
![Python](https://img.shields.io/badge/Python-3.12-yellow)

**按住一个键说话，松开后语音自动变成文字，直接打进游戏聊天框。**

默认使用 **SenseVoiceSmall(int8)** 在本机离线识别，录音不出本机；也支持任意
OpenAI 兼容的云端语音接口。通过 Windows 标准 `SendInput` 逐字输入，不依赖输入法，
中文、英文、数字、符号都能打。

[English README](README.en.md) · [下载](../../releases) · [问题反馈](../../issues) · [更新日志](CHANGELOG.md)

![界面](assets/screenshot.png)

---

## 功能

| 功能 | 说明 |
| --- | --- |
| 按住说话 / 切换说话 | 两种模式，按住模式接近对讲机 |
| 任意快捷键 | F1~F12、单字母、鼠标侧键（`mouse4`/`mouse5`）、组合键（`ctrl+alt+v`） |
| 自动开聊天框 + 自动发送 | 可分别关闭，留着文字自己改 |
| 仅在游戏窗口输入 | 不在目标窗口时只复制到剪贴板，避免把话打到桌面 |
| 识别修正词 | 把常听错的词映射成正确写法，例如 `a大=A大` |
| 数字规范化 | “三打二”自动写成 `3v2` 这类形式 |
| 离线 / 云端 | 默认本地 SenseVoice；也可填任意 OpenAI 兼容接口 |
| 提示音 | 开始录音、识别完成各有反馈，全屏游戏里也能听到 |
| 隐私 | 默认完全离线，不上传录音、不需要账号 |

识别语言：中文 / 英文 / 日文 / 韩文 / 粤语 / 自动。

---

## 下载与安装

### 方式一：安装程序（推荐）

1. 打开 [Releases](../../releases) 下载最新的 `VoiceInputTool-Setup-x.y.z.exe`；
2. 双击安装，按向导完成（**当前用户安装，不需要管理员权限**）；
3. 桌面/开始菜单会出现「语音输入工具」。

安装位置：`%LOCALAPPDATA%\Programs\VoiceInputTool`  
个人配置：`%LOCALAPPDATA%\VoiceInputTool\config.json`

### 方式二：便携版

下载 Release 中的 `VoiceInputTool-x.y.z-portable.zip`，解压后双击
`语音输入工具.exe`。整个文件夹可以放在任意位置。

> 程序未做代码签名，首次运行可能出现 SmartScreen 提示：
> 选择「更多信息 → 仍要运行」。

---

## 第一次使用

1. 打开程序，切到 **设置**；
2. 把 **输入设备** 选成真实麦克风（例如 `HECATE G2`），**不要**选 `MIXLINE`
   等虚拟声卡/混音设备；
3. 点 **保存并应用**；
4. 进游戏，按住 **F8** 说话，松开，文字会自动进入聊天框。

如果游戏内打不出字：关闭程序，右键 `语音输入工具.exe` →
**以管理员身份运行**（游戏进程权限更高时，Windows 会拦截普通程序的按键注入）。

---

## 隐私与风险

- **默认离线**：音频只在本机内存中处理，识别完即丢弃，不写文件、不上传；
- **云端模式**：只有你主动选择云端并填写 API Key 后，音频才会发给对应服务商；
- **不读内存、不注入进程、不改游戏文件**：程序只录音 + 调用 `SendInput`；
- 但第三方按键注入在各家反作弊中属于灰色地带，**请自行评估风险**；
- 想零注入风险：勾选「只复制到剪贴板，不模拟按键」。

本项目与 Riot Games、Valorant、FunASR、SenseVoice、sherpa-onnx 的维护者无隶属关系。

---

## 从源码运行

要求：Windows 10/11 x64、Python 3.10+（推荐 3.12）。

```powershell
git clone https://github.com/XIA1249218726/voice-input-tool.git
cd voice-input-tool

# 安装依赖 + 下载 228 MB 模型
powershell -ExecutionPolicy Bypass -File scripts\setup-dev.ps1

# 启动
powershell -ExecutionPolicy Bypass -File scripts\run.ps1

# 自检（依赖/模型/麦克风/权限）
powershell -ExecutionPolicy Bypass -File scripts\selftest.ps1

# 单元测试
powershell -ExecutionPolicy Bypass -File scripts\test.ps1
```

也可以直接：

```bat
python main.py
python main.py --selftest
python main.py --headless
```

模型默认放在 `models/sense-voice/`（已被 `.gitignore` 排除）。
详见 [models/README.md](models/README.md)。

---

## 打包

需要 PyInstaller 与 NSIS 3.x：

```powershell
# 便携版 -> dist\语音输入工具\
powershell -ExecutionPolicy Bypass -File build\build_app.ps1

# 安装程序 -> dist\VoiceInputTool-Setup-1.0.0.exe
powershell -ExecutionPolicy Bypass -File build\build_installer.ps1
```

打 tag 后 GitHub Actions 会自动构建并发布：

```powershell
git tag v1.0.1
git push origin v1.0.1
```

详细步骤见 [docs/05-打包与安装.md](docs/05-打包与安装.md)。

---

## 项目结构

```text
voice-input-tool/
├─ main.py                 入口、自检、单实例
├─ app/
│  ├─ paths.py             资源/用户数据目录解析
│  ├─ config.py            配置读写、类型校验、原子保存
│  ├─ audio.py             麦克风采集、预录缓冲、VAD、WAV
│  ├─ asr.py               本地 SenseVoice / 云端接口、后处理
│  ├─ hotkey.py            全局键盘/鼠标热键
│  ├─ winapi.py            SendInput、前台窗口、剪贴板
│  ├─ service.py           核心状态机
│  └─ gui.py               tkinter 界面
├─ build/                  PyInstaller / NSIS 脚本
├─ scripts/                安装、下载模型、运行、测试
├─ tests/                  单元测试
├─ docs/                   架构、模块、配置、修复报告
├─ models/                 模型目录（权重不提交）
├─ assets/                 截图
├─ config.example.json
└─ app.ico
```

更多文档：

- [架构与数据流](docs/01-架构与数据流.md)
- [模块详解](docs/02-模块详解.md)
- [配置项参考](docs/03-配置项参考.md)
- [问题修复报告](docs/04-问题修复报告.md)
- [测试与自检](docs/06-测试与自检.md)

---

## 常见问题

**松开后没反应 / 状态一直是“待命”**
- 快捷键被其它软件占用；换一个键；
- 麦克风选错（常见是选了 MIXLINE 虚拟声卡）；
- 用「录音 3 秒并识别」先验证录音链路。

**游戏里打不出字**
- 以管理员身份运行；
- 关闭「仅在游戏窗口激活时输入」再试；
- 游戏使用「无边框窗口」模式，全屏独占可能遮挡窗口。

**识别不准**
- 说话稍慢、离麦近一点；
- 在「设置 → 识别修正」加 `听错的词=正确的词`；
- 环境噪音大时降低增益或开启降噪。

**笔记本 CPU 较弱**
- 设置 → 识别引擎 → 云端接口，填入任意 OpenAI 兼容服务；
- 注意云端模式会上传音频。

**会不会封号？**
- 程序不读内存、不注入进程；但按键注入属于灰色地带，风险自担；
- 只复制到剪贴板模式没有按键注入。

---

## 参与贡献

欢迎 Issue 和 PR。请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全问题请按 [SECURITY.md](SECURITY.md)
私下报告，不要公开 Issue。

## 许可证

源代码使用 [MIT License](LICENSE)。
模型、依赖与打包工具的许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

维护者发布新版本请参考 [PUBLISH.md](PUBLISH.md) 和
[docs/07-发布与版本.md](docs/07-发布与版本.md)。
