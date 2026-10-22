# 发布到 GitHub

当前状态：

- 本地仓库：`D:\deepseek\voice-input-tool`
- 首次提交：`feat: initial open-source release v1.0.0`
- 标签：`v1.0.0`
- Git remote：`origin` → `https://github.com/XIA1249218726/voice-input-tool.git`
- GitHub 仓库：**尚未创建**（需要你在浏览器里点一下）

Git 已安装在 `E:\Git`，新开的终端可以直接使用 `git`。

## 1. 创建空仓库

打开：

```text
https://github.com/new?name=voice-input-tool&visibility=public
```

- Owner 选 `XIA1249218726`
- Repository name：`voice-input-tool`
- **不要**勾选 Add a README / .gitignore / license
- 点击 Create repository

## 2. 推送

```powershell
cd D:\deepseek\voice-input-tool
git push -u origin main
git push origin v1.0.0
```

第一次推送会弹出 Git Credential Manager 的 GitHub 登录窗口，按提示授权即可。
如果没有弹窗，可以手动登录：

```powershell
git credential-manager github login
```

也可以使用仓库自带脚本（会检查 remote、提交未保存改动、推送 main 和 tag）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\publish.ps1 `
  -RepoUrl https://github.com/XIA1249218726/voice-input-tool.git
```

## 3. 开启 Actions 写权限

推送 tag 后会自动触发 `.github/workflows/release.yml`，但首次使用前请确认：

**Settings → Actions → General → Workflow permissions** 选择
**Read and write permissions**，保存。

然后打开 **Actions** 页面查看构建。首次约 10~20 分钟，主要耗时是下载 228 MB 模型和
NSIS 压缩。构建成功后 Release 里会有：

- `VoiceInputTool-Setup-1.0.0.exe`
- `VoiceInputTool-1.0.0-portable.zip`

## 4. 仓库信息

About 描述建议：

> Windows 离线语音输入工具：按住快捷键说话，松开自动把文字打进游戏聊天框。SenseVoice + SendInput，无需输入法。

Topics：

```text
speech-to-text  asr  sensevoice  sherpa-onnx  windows  tkinter
voice-input  gaming  offline  python  pyinstaller  nsis
```

## 5. 建议开启的安全设置

- **Settings → Security → Private vulnerability reporting**：开启，配合 `SECURITY.md`；
- **Settings → Security → Code security and analysis**：Dependabot alerts、Secret scanning；
- **Settings → General → Features**：Issues、Discussions（可选）。

## 6. 如果仓库改名

如果不想用 `voice-input-tool` 这个名字，改完 GitHub 仓库名后执行：

```powershell
git remote set-url origin https://github.com/XIA1249218726/<new-name>.git
```

并全局替换仓库里的 `XIA1249218726/voice-input-tool`：

- `README.md`、`README.en.md` 的 clone 地址
- `.github/ISSUE_TEMPLATE/config.yml` 的 Security / Discussions 链接
- `PUBLISH.md` 中的命令

## 7. 不要提交的东西

`.gitignore` 已排除：

- `models/sense-voice/`（228 MB，用户运行脚本下载）
- `dist/`、`dist_raw/`、`_build/`、`runtime/`
- `config.json`、`logs/`、`userdata/`
- `*.exe`、`*.zip`、`*.msi`

仓库本身只有约 0.25 MB，发布包通过 GitHub Releases 分发。

## 8. 检查清单

- [ ] GitHub 上已创建空仓库
- [ ] `git push -u origin main` 成功
- [ ] `git push origin v1.0.0` 成功
- [ ] Actions 中 Release 工作流通过
- [ ] Release 里两个产物都能下载
- [ ] 在另一台 Windows 上安装并自检通过

## 9. 后续发布

```powershell
# 修改版本号后
git add .
git commit -m "release: v1.0.1"
git tag v1.0.1
git push origin main
git push origin v1.0.1
```

详见 [docs/07-发布与版本.md](docs/07-发布与版本.md)。
