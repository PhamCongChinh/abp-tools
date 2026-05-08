#!/bin/bash

echo "Creating virtual environment..."
python3 -m venv .env

echo "Activating virtual environment..."
source .env/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo "Run './run.sh' to start the application."
