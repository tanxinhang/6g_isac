@echo off
chcp 65001 >nul
REM ISAC 文献综述 Web 可视化平台 — 一键启动

cd /d "%~dp0"

echo =====================================================
echo   ISAC 文献综述 Web 可视化平台
echo   面向6G的通信感知一体化 (ISAC)
echo =====================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python
    pause
    exit /b 1
)

echo [检查] 正在检查依赖...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo [安装] 正在安装 Flask...
    pip install flask
)

echo.
echo [启动] 正在启动 Web 服务器...
echo [访问] 请在浏览器中打开: http://127.0.0.1:5000
echo [提示] 按 Ctrl+C 可停止服务器
echo.

python app.py

pause
