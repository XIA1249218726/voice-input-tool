# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 和语义化版本。

## [Unreleased]

### Planned

- 更详细的多语言识别测试
- 托盘图标与最小化到托盘
- 可选的本地模型切换（SenseVoice / Paraformer）

## [1.0.0] - 2026-10-22

首个开源版本。

### Added

- 按住说话 / 切换说话两种触发模式
- 全局键盘热键、鼠标侧键、Ctrl/Alt/Shift/Win 组合键
- 本地离线 SenseVoiceSmall(int8) 识别，支持中/英/日/韩/粤语与自动识别
- 任意 OpenAI 兼容 `/audio/transcriptions` 云端接口
- `SendInput` Unicode 逐字输入，绕过输入法
- 自动打开游戏聊天框、自动发送、可选的「仅在游戏窗口激活时输入」
- 剪贴板模式（零按键注入）
- 识别修正词、数字/日期规范化、去句末标点
- 提示音、窗口置顶、麦克风选择、录音测试
- 用户数据目录自动选择与只读环境回退
- 单元测试（17 个）、自检模式、崩溃日志
- PyInstaller 便携版与 NSIS 简体中文安装程序
- GitHub Actions：CI 测试 + tag 自动构建 Release

### Fixed

- 64 位 Win32 窗口/进程句柄被截断的问题
- 麦克风启动失败时界面仍显示运行中的问题
- 录音缓冲超过上限后继续增长的问题
- 剪贴板写入失败时的内存泄漏与缺少重试
- 配置文件非原子写入、错误类型导致崩溃的问题
- 安装版配置写入只读目录失败的问题
- 虚拟声卡提醒永不触发的问题
- 热键监听线程的修饰键竞态
- 高分屏界面模糊
- 打包版自检没有控制台输出
- NSIS 脚本 UTF-8 BOM 与临时目录问题

### Security

- 默认本地识别，录音不出本机
- API Key 仅保存在本机配置文件
