@echo off
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
    python "tools\daily_check.py"
    goto :done
)
where py >nul 2>nul
if %errorlevel%==0 (
    py "tools\daily_check.py"
    goto :done
)
echo.
echo   [提示] 没有找到 Python，请先安装（安装时务必勾选 "Add Python to PATH"）：
echo          https://www.python.org/downloads/
echo   装好后重新双击本文件即可。
:done
echo.
pause
