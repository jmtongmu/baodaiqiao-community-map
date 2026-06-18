@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "REMOTE_URL=https://github.com/jmtongmu/baodaiqiao-community-map.git"

git --version >nul 2>nul
if errorlevel 1 (
  echo 未找到 Git，请先安装 Git for Windows。
  pause
  exit /b 1
)

git remote remove origin >nul 2>nul
git remote add origin "%REMOTE_URL%"

echo 即将推送到：
echo %REMOTE_URL%
echo.
echo 如果 GitHub 弹出登录窗口，请登录 jmtongmu 账号并授权。
echo 若提示 repository not found，请先在 GitHub 创建空仓库：baodaiqiao-community-map
echo.
git push -u origin main
pause
