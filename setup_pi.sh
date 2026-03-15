#!/bin/bash

# Exit on error
set -e

echo "🍓 RASPBERRY PI SETUP SCRIPT 🍓"
echo "Target OS: Raspberry Pi OS Bookworm (Debian 12)"

# 1. Update System
echo "🔄 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install System Dependencies
# libatlas-base-dev: for numpy
# portaudio19-dev: for pyaudio/sounddevice
# libopenblas-dev: math libraries
# libcamera-dev: camera support
# python3-venv: for creating virtual environments
# python3-opencv: system opencv (optional but good to have)
echo "📦 Installing system libraries..."
sudo apt install -y \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    libatlas-base-dev \
    portaudio19-dev \
    libopenblas-dev \
    libcamera-dev \
    v4l-utils

# 3. Create Virtual Environment
echo "🐍 Setting up Python Virtual Environment (.venv)..."
# We use --system-site-packages to allow access to system-installed python libs (like rpi.gpio if needed)
python3 -m venv .venv --system-site-packages

# 4. Activate and Install
echo "🔌 Activating .venv and installing dependencies..."
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python requirements
# Note: This might take a while for things like numpy/pandas if no wheels are found
echo "⏳ Installing Python packages from requirements_pi.txt..."
pip install -r requirements_pi.txt

echo "✅ Setup Complete!"
echo "👉 Run './run_pi.sh' to start the application."
