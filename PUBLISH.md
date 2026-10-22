# 发布与维护

## 当前状态

| 项目 | 值 |
| --- | --- |
| GitHub 仓库 | https://github.com/XIA1249218726/voice-input-tool |
| 默认分支 | `main` |
| 首次 Release | [v1.0.0](https://github.com/XIA1249218726/voice-input-tool/releases/tag/v1.0.0) |
| 安装程序 | `VoiceInputTool-Setup-1.0.0.exe` |
| 便携版 | `VoiceInputTool-1.0.0-portable.zip` |
| CI | `.github/workflows/ci.yml` 已通过 |
| Release 构建 | `.github/workflows/release.yml` 已通过 |

Git remote 已经配置：

```text
origin  https://github.com/XIA1249218726/voice-input-tool.git
```

本机 Git 安装在 `E:\Git`，新开的终端可以直接使用 `git`。

## 日常更新

```powershell
cd D:\deepseek\voice-input-tool

git status
git add -A
git commit -m "fix: 描述你的改动"
git push origin main
```

推送 `main` 会自动运行 CI（编译检查 + 单元测试）。模型不在仓库里，
CI 会跳过真实识别测试。

## 发布新版本

1. 修改版本号：

   | 文件 | 字段 |
   | --- | --- |
   | `app/paths.py` | `APP_VERSION` |
   | `build/version_info.txt` | `filevers` / `prodvers` / `FileVersion` / `ProductVersion` |
   | `build/installer.nsi` | `APP_VERSION` / `APP_VERSION4` |
   | `build/build_installer.ps1` | `-Version` 默认值 |
   | `CHANGELOG.md` | 新版本段落 |

2. 提交并打 tag：

   ```powershell
   git add .
   git commit -m "release: v1.0.1"
   git tag v1.0.1
   git push origin main
   git push origin v1.0.1
   ```

3. 打开仓库 **Actions**，等待 `Release` 工作流完成。它会自动：

   - 下载/缓存 SenseVoice 模型；
   - 构建便携版；
   - 安装 NSIS 并生成安装程序；
   - 打包便携版 zip；
   - 生成 `SHA256SUMS.txt`；
   - 创建 GitHub Release 并上传文件。

4. 在 Release 页面确认三个文件：

   - `VoiceInputTool-Setup-<version>.exe`
   - `VoiceInputTool-<version>-portable.zip`
   - `SHA256SUMS.txt`

## Actions 权限

首次发布前确认：

**Settings → Actions → General → Workflow permissions** 选择
**Read and write permissions**。

否则 `softprops/action-gh-release` 无法创建 Release。

## 仓库设置建议

About 描述：

> Windows 离线语音输入工具：按住快捷键说话，松开自动把文字打进游戏聊天框。SenseVoice + SendInput，无需输入法。

Topics：

```text
speech-to-text  asr  sensevoice  sherpa-onnx  windows  tkinter
voice-input  gaming  offline  python  pyinstaller  nsis
```

安全设置：

- **Settings → Security → Private vulnerability reporting**：开启，配合 `SECURITY.md`；
- **Settings → Security → Code security and analysis**：Dependabot alerts、Secret scanning；
- **Settings → General → Features**：Issues、Discussions（可选）。

## 不要提交的东西

`.gitignore` 已排除：

- `models/sense-voice/`（228 MB，用户运行脚本下载）
- `dist/`、`dist_raw/`、`_build/`、`runtime/`
- `config.json`、`logs/`、`userdata/`
- `*.exe`、`*.zip`、`*.msi`

仓库本身约 0.25 MB，发布包通过 GitHub Releases 分发。

## 检查清单

- [ ] CI 通过
- [ ] Release 工作流通过
- [ ] Release 里三个文件都能下载
- [ ] `SHA256SUMS.txt` 与文件匹配
- [ ] 在另一台 Windows 上安装并自检通过
- [ ] README 的截图 / 功能表与新版本一致
