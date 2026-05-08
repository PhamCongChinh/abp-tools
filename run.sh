#!/bin/bash

echo "Activating virtual environment..."
source .env/bin/activate

echo "Starting FastAPI application..."
python main.py
