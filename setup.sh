#!/bin/bash
# Quick setup script for ATS Resume Agent

echo "========================================="
echo "ATS Resume Agent - Setup Script"
echo "========================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env from example
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
else
    echo ""
    echo "✅ .env file already exists"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY"
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo "3. Run a test:"
echo "   python -m orchestrator.state_machine --input tests/sample_input.json --out out/result.json"
echo ""
echo "For more information, see README.md"
echo ""

