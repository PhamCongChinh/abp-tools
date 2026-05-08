@echo off
echo Activating virtual environment...
call .env\Scripts\activate.bat

echo Starting FastAPI application...
python main.py

pause
