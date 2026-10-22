; 语音输入工具 —— NSIS 安装程序脚本
; 编译：makensis /DAPP_SRC="...\dist\语音输入工具" /DOUTFILE="...\dist\VoiceInputTool-Setup-1.0.0.exe" installer.nsi
; 安装范围：当前用户（无需管理员，不写 Program Files，不弹 UAC）

Unicode true
SetCompressor /SOLID lzma
SetCompressorDictSize 64
RequestExecutionLevel user
ManifestDPIAware true

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

!ifndef APP_NAME
  !define APP_NAME "语音输入工具"
!endif
!ifndef APP_VERSION
  !define APP_VERSION "1.0.0"
!endif
!ifndef APP_VERSION4
  !define APP_VERSION4 "1.0.0.0"
!endif
!ifndef APP_EXE
  !define APP_EXE "语音输入工具.exe"
!endif
!ifndef APP_SRC
  !define APP_SRC "..\dist\语音输入工具"
!endif
!ifndef OUTFILE
  !define OUTFILE "..\dist\VoiceInputTool-Setup-${APP_VERSION}.exe"
!endif
!ifndef APP_ICON
  !define APP_ICON "..\app.ico"
!endif

!define APP_ID "VoiceInputTool"
!define APP_PUBLISHER "VoiceInputTool contributors"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"
!define APP_REG_KEY "Software\${APP_ID}"

Name "${APP_NAME}"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\Programs\${APP_ID}"
InstallDirRegKey HKCU "${APP_REG_KEY}" "InstallDir"
BrandingText "${APP_NAME} ${APP_VERSION}"
Icon "${APP_ICON}"
UninstallIcon "${APP_ICON}"
WindowIcon on
ShowInstDetails show
ShowUninstDetails show
AutoCloseWindow false
XPStyle on

VIProductVersion "${APP_VERSION4}"
VIAddVersionKey /LANG=2052 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=2052 "FileDescription" "${APP_NAME} 安装程序"
VIAddVersionKey /LANG=2052 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=2052 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=2052 "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=2052 "LegalCopyright" "Copyright (c) 2026 VoiceInputTool contributors"

!define MUI_ABORTWARNING
!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"
!define MUI_WELCOMEPAGE_TITLE "${APP_NAME} ${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "按住快捷键说话，松开后文字自动进入游戏聊天框。$\r$\n$\r$\n本程序完全离线运行，语音不会离开你的电脑。$\r$\n$\r$\n安装到当前用户目录，不需要管理员权限。"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "立即启动 ${APP_NAME}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

LangString DESC_SEC_MAIN ${LANG_SIMPCHINESE} "程序本体、离线识别模型和使用说明（必装）。"
LangString DESC_SEC_DESKTOP ${LANG_SIMPCHINESE} "在桌面创建「语音输入工具」快捷方式。"
LangString DESC_SEC_STARTUP ${LANG_SIMPCHINESE} "开机时自动启动，并在后台待命（可选）。"

; 安装前先结束正在运行的旧版本，避免文件被占用
Function .onInit
  nsExec::Exec 'taskkill /F /IM "${APP_EXE}"'
  Pop $0
FunctionEnd

Section "核心程序（必装）" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /r "${APP_SRC}\*.*"

  WriteUninstaller "$INSTDIR\uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe"

  WriteRegStr HKCU "${APP_REG_KEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${APP_REG_KEY}" "Version" "${APP_VERSION}"

  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKCU "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "${UNINST_KEY}" "EstimatedSize" "$0"
SectionEnd

Section "桌面快捷方式" SecDesktop
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

Section /o "开机自动启动" SecStartup
  CreateShortCut "$SMSTARTUP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SEC_MAIN)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_SEC_DESKTOP)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} $(DESC_SEC_STARTUP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  SetOutPath "$TEMP"
  nsExec::Exec 'taskkill /F /IM "${APP_EXE}"'

  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMSTARTUP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  RMDir /r "$INSTDIR\_internal"
  RMDir /r "$INSTDIR\models"
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\app.ico"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\使用说明.txt"
  Delete "$INSTDIR\自检.bat"
  Delete "$INSTDIR\config.example.json"
  RMDir /r "$INSTDIR\userdata"
  Delete "$INSTDIR\uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "${UNINST_KEY}"
  DeleteRegKey HKCU "${APP_REG_KEY}"

  IfSilent keepdata
  MessageBox MB_YESNO|MB_ICONQUESTION "是否同时删除个人设置和日志（$LOCALAPPDATA\${APP_ID}）？$\r$\n选择「否」会保留，下次安装仍然可用。" IDNO keepdata
  RMDir /r "$LOCALAPPDATA\${APP_ID}"
  keepdata:
SectionEnd
