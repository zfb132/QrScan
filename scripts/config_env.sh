#!/bin/bash

# script will exit when a command occurs error
set -e

echo Creating virtual environment: venv
python3 -m venv venv
echo Upgrade pip version
venv/bin/python -m pip install --upgrade pip
echo Installing pyqt5 pyqt5-stubs pywin32 pyinstaller opencv-python opencv-contrib-python
venv/bin/pip install -r requirements.txt