# 贡献指南

感谢你愿意改进语音输入工具。请先阅读以下约定，能显著减少来回沟通。

## 开发环境

- Windows 10/11 x64
- Python 3.10+（推荐 3.12）
- 麦克风（测试录音链路时需要）

```powershell
git clone https://github.com/<your-name>/voice-input-tool.git
cd voice-input-tool
powershell -ExecutionPolicy Bypass -File scripts\setup-dev.ps1 -Venv
powershell -ExecutionPolicy Bypass -File scripts\run.ps1
```

模型约 228 MB，`setup-dev.ps1` 会自动下载到 `models/sense-voice/`（已被 Git 忽略）。
如果只想跑单元测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test.ps1
```

## 不要提交

- `models/` 下的模型权重（约 228 MB）
- `dist/`、`dist_raw/`、`_build/`、`runtime/`、`*.exe`
- `config.json`、`logs/`、`userdata/`（含个人设备名/API Key）
- 任何 API Key、令牌、个人信息

## 代码风格

- Python 3.10+ 语法，尽量保持与现有模块一致的命名和中文注释；
- 新增行为要有对应的单元测试（`tests/`）；
- 不引入重量级新依赖；确需引入时先开 Issue 讨论；
- Win32 调用必须显式声明 `argtypes/restype`，避免 64 位句柄截断；
- GUI 代码不得在非主线程直接操作 tkinter 控件；
- 配置新增字段时同步更新 `app/config.py`、`config.example.json`、`docs/03-配置项参考.md`。

## 提交信息

使用 Conventional Commits 风格：

```text
feat: 增加按一下开始/再按结束模式
fix: 修正麦克风设备名匹配
docs: 补充打包说明
test: 覆盖静音裁剪边界
```

## Pull Request

1. Fork 并创建分支：`feat/xxx` / `fix/xxx`；
2. 确保 `scripts\test.ps1` 通过；
3. 说明改动动机、行为变化和测试方式；
4. 涉及 UI 的改动请附截图/GIF；
5. 不要在一个 PR 里混入无关格式化。

## 发布

维护者通过 tag 触发 GitHub Actions 自动构建：

```powershell
git tag v1.0.1
git push origin v1.0.1
```

工作流会生成便携版 zip 和安装程序，并创建 GitHub Release。

## 问题反馈

- Bug：使用 Bug Report 模板，附 Windows 版本、日志（`%LOCALAPPDATA%\VoiceInputTool\logs\`）、复现步骤；
- 功能建议：说明使用场景，而不只是实现方式；
- 安全问题：不要公开 Issue，见 [SECURITY.md](SECURITY.md)。
