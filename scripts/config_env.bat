@echo off
color a
echo �������⻷��venv
python -m venv venv
echo ����pip�汾
.\venv\Scripts\python.exe -m pip install --upgrade pip
echo ��װpyqt5 pyqt5-stubs pywin32 pyinstaller opencv-python opencv-contrib-python
.\venv\Scripts\pip.exe install -r requirements.txt