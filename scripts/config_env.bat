@echo off
color a
echo 创建虚拟环境venv
python -m venv venv
echo 升级pip版本
.\venv\Scripts\python.exe -m pip install --upgrade pip
echo 安装pyqt5 pyqt5-stubs pywin32 pyinstaller opencv-python opencv-contrib-python
.\venv\Scripts\pip.exe install -r requirements.txt