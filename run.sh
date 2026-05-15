#!/bin/bash

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Starting FastAPI application..."
python main.py
