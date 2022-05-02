#!/bin/bash

# script will exit when a command occurs error
set -e

echo 创建虚拟环境venv
python3 -m venv venv
echo 升级pip版本
venv/bin/python -m pip install --upgrade pip
echo 安装pyqt5 pyqt5-stubs pywin32 pyinstaller opencv-python opencv-contrib-python
venv/bin/pip install -r requirements.txt