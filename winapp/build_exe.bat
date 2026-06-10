@echo off
REM 一键打包 KWEngine.exe — 在 Windows 上双击运行（需要 Python 3.10+）
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [!] 未找到 Python。请先从 https://www.python.org/downloads/ 安装 Python 3.10+，
    echo     安装时勾选 "Add python.exe to PATH"。
    pause
    exit /b 1
)

echo ^>^> Creating virtual environment ...
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo ^>^> Installing dependencies ...
python -m pip install --upgrade pip -q
pip install -e . -q
pip install pyinstaller -q

echo ^>^> Building KWEngine.exe (clean) ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller kwengine.spec --noconfirm

if exist dist\KWEngine.exe (
    echo.
    echo [OK] 完成: %cd%\dist\KWEngine.exe
) else (
    echo.
    echo [X] 构建失败，请查看上方输出。
)
pause
