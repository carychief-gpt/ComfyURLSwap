@echo off
rem 一键重新打包 ComfyURLSwap.exe（输出到 dist\ 目录）
cd /d "%~dp0.."
py -m pip install pyinstaller --quiet --disable-pip-version-check
py -m PyInstaller --noconfirm --clean --onefile --windowed ^
   --name ComfyURLSwap --icon tools\app.ico --add-data "tools\app.ico;." main.py
echo.
if exist dist\ComfyURLSwap.exe (
    echo 打包完成: dist\ComfyURLSwap.exe
) else (
    echo 打包失败，请查看上方日志
)
pause
