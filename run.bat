@echo off
title SpotifyXRefer Bot
cd /d "%~dp0"
echo [1/2] Installing requirements...
pip install -r requirements.txt
echo [2/2] Starting bot...
python bot.py
pause