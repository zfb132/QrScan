@echo off
REM ����������ɫ
color a
echo -----------------�Զ����PyQt��ĿΪexe------------------
echo ���û�������
REM ���õ�ǰ����Ŀ¼D:\python\qr_scan\gui
set PRJ_PATH=%~dp0
REM ���õ�ǰ����ļ�������Ҫд·��������Ҫд��չ����
set PY_NAME=pyqt5_qr_scan
REM �������⻷������
set PYTHON_NAME=venv
REM ����pyinstall.exe
set PYINSTALLER_FILE=%PRJ_PATH%\%PYTHON_NAME%\Scripts\pyinstaller.exe
REM ����PyQT5�����ӿ�·��
set PYQT_PATH=%PRJ_PATH%\%PYTHON_NAME%\Lib\site-packages\PyQt5\Qt\bin
REM ����.spec�ļ��ı���·��
set SPEC_PATH=%PRJ_PATH%\build
REM ����pyinstaller����·��
set WORK_PATH=%PRJ_PATH%\build
REM ���ô������ļ��Ĵ��·��
set DIST_PATH=%PRJ_PATH%\bin
REM ����ͼ���ļ�
set ICON_FILE=%PRJ_PATH%\qrscan.ico
REM �������հ汾�ĳ���·��
set FINAL_PATH=QrScan

REM �����ϴε��ļ�
rmdir /Q /S %WORK_PATH%
rmdir /Q /S %DIST_PATH%
del resources.py

REM ץȡĳ���ļ��İ汾����
REM %PRJ_PATH%\%PYTHON_NAME%\Scripts\python.exe %PRJ_PATH%\%PYTHON_NAME%\Lib\site-packages\PyInstaller\utils\cliutils grab_version.py demo.exe

REM ����Qt��ͼƬ��Դ�ļ�
%PRJ_PATH%\%PYTHON_NAME%\Scripts\pyrcc5.exe resources.qrc -o resources.py

REM Analysis.py���������-y��ʾ�Զ��Ƴ�ǰһ�ε������ļ���  --icon=%ICON_FILE%
echo ���ڶ�Analysis.py���
%PYINSTALLER_FILE% --paths=%PYQT_PATH%  --specpath=%SPEC_PATH% --workpath=%WORK_PATH% --distpath=%DIST_PATH% --key 8rdf-#875FGSDyrd7t --version-file %PRJ_PATH%\file_version_info.txt --icon=%ICON_FILE% -D -w %PRJ_PATH%\%PY_NAME%.py -y

REM �����ļ������ڴ�����հ汾
echo �����ļ���%FINAL_PATH%
rename "%DIST_PATH%\%PY_NAME%" "%FINAL_PATH%"
md %DIST_PATH%\%FINAL_PATH%\models

REM ��models�ļ��е����ݸ��Ƶ�%FINAL_PATH%�ļ��У�����ԭ�ļ����ݹ鸴����Ŀ¼��
REM xcopy /y "%DIST_PATH%/control" "%FINAL_PATH%\" /e
xcopy /y models\ %DIST_PATH%\%FINAL_PATH%\models /e

cd %DIST_PATH%\
tar.exe -a -c -f %FINAL_PATH%.zip %FINAL_PATH%
move %FINAL_PATH%.zip %PRJ_PATH%
cd %PRJ_PATH%

REM pause