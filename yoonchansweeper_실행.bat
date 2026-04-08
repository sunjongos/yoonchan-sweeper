@echo off
title YoonchanSweeper
chcp 65001 >nul
cd /d "%~dp0"
echo YoonchanSweeper 매크로를 실행합니다...
python yoonchan_sweeper.py
pause
