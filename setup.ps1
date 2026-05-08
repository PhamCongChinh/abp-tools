# PowerShell script to setup the project

Write-Host "Creating virtual environment..." -ForegroundColor Green
python -m venv .env

Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\.env\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Run 'run.ps1' or 'run.bat' to start the application." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
