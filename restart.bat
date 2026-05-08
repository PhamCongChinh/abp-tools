@echo off
echo Restarting FastAPI server...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
call .env\Scripts\activate.bat
python main.py
