@echo off
rem ComfyURLSwap 启动脚本（优先无窗口 pythonw，失败则回退 python）
cd /d "%~dp0"
pythonw main.py 2>nul
if errorlevel 1 python main.py
