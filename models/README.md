# 离线识别模型

本目录用于放置 **SenseVoiceSmall int8** 模型，模型文件约 228 MB，**不提交到 Git**。

## 自动下载

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download-model.ps1
```

脚本会下载：

```text
https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/
  sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2
```

解压后目录结构：

```text
models/sense-voice/
├─ model.int8.onnx   （约 228 MB）
├─ tokens.txt
├─ LICENSE
├─ README.md
└─ test_wavs/        （自检/测试用）
```

脚本会校验 `model.int8.onnx` 的 SHA256：

```text
C71F0CE00BEC95B07744E116345E33D8CBBE08CEF896382CF907BF4B51A2CD51
```

## 手动下载

1. 下载上面的 `.tar.bz2`；
2. 解压；
3. 把解压出的 `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/` 内容
   放到 `models/sense-voice/`（确保 `model.int8.onnx` 和 `tokens.txt` 直接位于该目录）。

## 许可证

模型权重来自 [FunASR / SenseVoice](https://github.com/modelscope/FunASR)，遵循 MIT 许可证。
详见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

## 使用云端识别

如果不想下载模型，可以在程序「设置 → 识别引擎」里选择云端接口，
填入任意 OpenAI 兼容的 `/audio/transcriptions` 服务。
