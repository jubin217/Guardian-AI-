#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Activate Virtual Environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found! Run ./setup_pi.sh first."
    exit 1
fi

# Run the application
echo "🚀 Starting Emergency Decision Engine on Pi..."
python3 main.py
