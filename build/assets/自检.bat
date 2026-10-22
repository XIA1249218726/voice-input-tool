@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo 正在自检，请稍候（加载离线模型约需 1~3 秒）...
start "" /wait "%~dp0语音输入工具.exe" --selftest

timeout /t 1 /nobreak >nul
set "REPORT=%LOCALAPPDATA%\VoiceInputTool\logs\selftest.txt"
if not exist "%REPORT%" set "REPORT=%~dp0userdata\logs\selftest.txt"
if exist "%REPORT%" (
    type "%REPORT%"
) else (
    echo 自检报告没有生成，请把本窗口截图反馈。
)
echo.
pause
