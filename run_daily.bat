@echo off
REM 设置窗口标题
title Daily Task Runner

REM 切换到批处理文件所在的目录, 确保能找到 ts.exe
cd /d "%~dp0"

echo Starting ts.exe in daily mode...
echo The program will run in this window. Do not close it.
echo.

REM 执行 ts.exe
ts.exe --daily --time 05:00

echo.
echo Program has exited.
pause
