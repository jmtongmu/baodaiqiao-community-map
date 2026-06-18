@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PORT=8282"

where python >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=python"
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
  ) else (
    echo 未找到 Python。请先安装 Python 3，或在已安装 Python 的电脑上运行。
    echo.
    pause
    exit /b 1
  )
)

echo 正在启动宝带桥社区志 AIGC 地图...
echo 本地地址：http://127.0.0.1:%PORT%/
echo.
echo 请不要关闭这个窗口；关闭窗口后网页服务也会停止。
start "" "http://127.0.0.1:%PORT%/"
%PYTHON_CMD% -m http.server %PORT% --bind 127.0.0.1
pause
