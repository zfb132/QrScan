@echo off
REM 设置字体颜色
color a
echo -----------------自动打包PyQt项目为exe------------------
echo 设置环境变量
REM 设置当前工作目录D:\python\qr_scan\gui
set PRJ_PATH=%~dp0
REM 设置当前打包文件（不需要写路径，不需要写扩展名）
set PY_NAME=pyqt5_qr_scan
REM 设置虚拟环境名称
set PYTHON_NAME=venv
REM 设置pyinstall.exe
set PYINSTALLER_FILE=%PRJ_PATH%\%PYTHON_NAME%\Scripts\pyinstaller.exe
REM 设置PyQT5的链接库路径
set PYQT_PATH=%PRJ_PATH%\%PYTHON_NAME%\Lib\site-packages\PyQt5\Qt\bin
REM 设置.spec文件的保存路径
set SPEC_PATH=%PRJ_PATH%\build
REM 设置pyinstaller工作路径
set WORK_PATH=%PRJ_PATH%\build
REM 设置打包输出文件的存放路径
set DIST_PATH=%PRJ_PATH%\bin
REM 设置图标文件
set ICON_FILE=%PRJ_PATH%\qrscan.ico
REM 设置最终版本的程序路径
set FINAL_PATH=QrScan

REM 清理上次的文件
rmdir /Q /S %WORK_PATH%
rmdir /Q /S %DIST_PATH%
del resources.py

REM 抓取某个文件的版本数据
REM %PRJ_PATH%\%PYTHON_NAME%\Scripts\python.exe %PRJ_PATH%\%PYTHON_NAME%\Lib\site-packages\PyInstaller\utils\cliutils grab_version.py demo.exe

REM 编译Qt的图片资源文件
%PRJ_PATH%\%PYTHON_NAME%\Scripts\pyrcc5.exe resources.qrc -o resources.py

REM Analysis.py打包，其中-y表示自动移除前一次的生成文件夹  --icon=%ICON_FILE%
echo 正在对Analysis.py打包
%PYINSTALLER_FILE% --paths=%PYQT_PATH%  --specpath=%SPEC_PATH% --workpath=%WORK_PATH% --distpath=%DIST_PATH% --key 8rdf-#875FGSDyrd7t --version-file %PRJ_PATH%\file_version_info.txt --icon=%ICON_FILE% -D -w %PRJ_PATH%\%PY_NAME%.py -y

REM 创建文件夹用于存放最终版本
echo 创建文件夹%FINAL_PATH%
rename "%DIST_PATH%\%PY_NAME%" "%FINAL_PATH%"
md %DIST_PATH%\%FINAL_PATH%\models

REM 把models文件夹的内容复制到%FINAL_PATH%文件夹（覆盖原文件、递归复制子目录）
REM xcopy /y "%DIST_PATH%/control" "%FINAL_PATH%\" /e
xcopy /y models\ %DIST_PATH%\%FINAL_PATH%\models /e

cd %DIST_PATH%\
tar.exe -a -c -f %FINAL_PATH%.zip %FINAL_PATH%
move %FINAL_PATH%.zip %PRJ_PATH%
cd %PRJ_PATH%

REM pause