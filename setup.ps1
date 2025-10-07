# Quick setup script for ATS Resume Agent (PowerShell)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "ATS Resume Agent - Setup Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Found $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Create .env from example
if (!(Test-Path .env)) {
    Write-Host ""
    Write-Host "Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item env.example .env
    Write-Host "⚠️  Please edit .env and add your API keys!" -ForegroundColor Yellow
}
else {
    Write-Host ""
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY"
Write-Host "2. Activate the virtual environment:"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "3. Run a test:"
Write-Host "   python -m orchestrator.state_machine --input tests/sample_input.json --out out/result.json"
Write-Host ""
Write-Host "For more information, see README.md" -ForegroundColor Cyan
Write-Host ""

