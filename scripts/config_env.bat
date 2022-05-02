@echo off
color a
echo Creating virtual environment: venv
python -m venv venv
echo Upgrade pip version
.\venv\Scripts\python.exe -m pip install --upgrade pip
echoInstalling pyqt5 pyqt5-stubs pywin32 pyinstaller opencv-python opencv-contrib-python
.\venv\Scripts\pip.exe install -r requirements.txt