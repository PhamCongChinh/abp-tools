# PowerShell script to activate venv and run FastAPI

Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\.env\Scripts\Activate.ps1

Write-Host "Starting FastAPI application..." -ForegroundColor Green
python main.py

Read-Host "Press Enter to exit"
