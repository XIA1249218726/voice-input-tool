# 第三方组件与许可证说明

本项目的 **源代码** 使用 [MIT License](LICENSE)。

发布的可执行文件/安装包中包含以下第三方组件。各组件的版权归其作者所有，
并继续遵循各自的许可证。本仓库不包含模型权重和便携 Python 运行时。

## 识别模型

| 组件 | 许可证 | 说明 |
| --- | --- | --- |
| SenseVoiceSmall (int8) | MIT（FunASR） | 模型权重不提交到本仓库，由 `scripts/download-model.ps1` 下载；模型卡与许可证见 [FunASR](https://github.com/modelscope/FunASR) 与 [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) |
| sherpa-onnx | Apache-2.0 | 推理运行时，[k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) |
| ONNX Runtime | MIT | [microsoft/onnxruntime](https://github.com/microsoft/onnxruntime) |

## Python 依赖

| 组件 | 许可证 | 项目地址 |
| --- | --- | --- |
| numpy | BSD-3-Clause | https://github.com/numpy/numpy |
| sounddevice | MIT | https://github.com/spatialaudio/python-sounddevice |
| PortAudio | MIT | https://github.com/PortAudio/portaudio |
| pynput | LGPL-3.0 | https://github.com/moses-palmer/pynput |
| requests | Apache-2.0 | https://github.com/psf/requests |
| urllib3 | MIT | https://github.com/urllib3/urllib3 |
| certifi | MPL-2.0 | https://github.com/certifi/python-certifi |
| charset-normalizer | MIT | https://github.com/jawah/charset_normalizer |
| idna | BSD-3-Clause | https://github.com/kjd/idna |
| cffi | MIT | https://github.com/python-cffi/cffi |
| pycparser | BSD-3-Clause | https://github.com/eliben/pycparser |
| six | MIT | https://github.com/benjaminp/six |

## 打包与安装工具（仅构建时使用）

| 组件 | 许可证 | 说明 |
| --- | --- | --- |
| PyInstaller | GPL-2.0-or-later，附「bootloader exception」 | 允许把打包后的应用以其他许可证分发；PyInstaller 本身不包含在源码中 |
| NSIS | zlib/libpng license | 仅用于生成 Windows 安装程序 |
| Tcl/Tk | BSD-style | Python 标准库 tkinter 的运行时 |

## LGPL 说明（pynput）

pynput 以 LGPL-3.0 发布。发布的可执行文件中包含其未修改的字节码/源码副本。
如需替换该库，可从上述项目地址获取对应版本源码，并参考 PyInstaller 文档重新打包。
本项目未修改 pynput。

## 免责声明

本项目与 Riot Games、Valorant、FunASR、SenseVoice、sherpa-onnx 的维护者无隶属关系。
游戏内使用按键注入可能违反游戏服务条款，风险由使用者自行承担。
