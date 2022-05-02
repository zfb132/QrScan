@echo off
REM Set color in terminal
color a
echo -----------------Publish PyQt project to exe------------------
echo Set environment variables
REM Set current work dir
set PRJ_PATH=%~dp0
REM Set python code file name
set PY_NAME=pyqt5_qr_scan
REM Set virtual environment name
set PYTHON_NAME=venv
REM set path of pyinstall.exe
set PYINSTALLER_FILE=%PRJ_PATH%\%PYTHON_NAME%\Scripts\pyinstaller.exe
REM set lib of PyQT5
set PYQT_PATH=%PRJ_PATH%\%PYTHON_NAME%\Lib\site-packages\PyQt5\Qt\bin
set SPEC_PATH=%PRJ_PATH%\build
set WORK_PATH=%PRJ_PATH%\build
set DIST_PATH=%PRJ_PATH%\bin
set ICON_FILE=%PRJ_PATH%\qrscan.ico
set FINAL_PATH=QrScan

rmdir /Q /S %WORK_PATH%
rmdir /Q /S %DIST_PATH%
del resources.py

REM how to get version.txt template
REM %PRJ_PATH%\%PYTHON_NAME%\Scripts\python.exe %PRJ_PATH%\%PYTHON_NAME%\Lib\site-packages\PyInstaller\utils\cliutils grab_version.py demo.exe

REM compile images
%PRJ_PATH%\%PYTHON_NAME%\Scripts\pyrcc5.exe resources.qrc -o resources.py

echo Packing Analysis.py
%PYINSTALLER_FILE% --paths=%PYQT_PATH%  --specpath=%SPEC_PATH% --workpath=%WORK_PATH% --distpath=%DIST_PATH% --key 8rdf-#875FGSDyrd7t --version-file %PRJ_PATH%\file_version_info.txt --icon=%ICON_FILE% -D -w %PRJ_PATH%\%PY_NAME%.py -y

echo Creating %FINAL_PATH%
rename "%DIST_PATH%\%PY_NAME%" "%FINAL_PATH%"
md %DIST_PATH%\%FINAL_PATH%\models

REM xcopy /y "%DIST_PATH%/control" "%FINAL_PATH%\" /e
xcopy /y models\ %DIST_PATH%\%FINAL_PATH%\models /e

cd %DIST_PATH%\
tar.exe -a -c -f %FINAL_PATH%.zip %FINAL_PATH%
move %FINAL_PATH%.zip %PRJ_PATH%
cd %PRJ_PATH%

REM pause