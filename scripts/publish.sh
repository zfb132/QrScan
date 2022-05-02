#!/bin/bash

# script will exit when a command occurs error
set -e

export PRJ_PATH=$(pwd)
export PY_NAME=pyqt5_qr_scan
export PYTHON_NAME=venv
export PYINSTALLER_FILE=${PRJ_PATH}/${PYTHON_NAME}/bin/pyinstaller
export PY_VER=python$(venv/bin/python3 -V | cut -d " " -f 2 | cut -d "." -f 1-2)
export PYQT_PATH=${PRJ_PATH}/${PYTHON_NAME}/lib/${PY_VER}/site-packages/PyQt5/Qt5/lib
export SPEC_PATH=${PRJ_PATH}/build
export WORK_PATH=${PRJ_PATH}/build
export DIST_PATH=${PRJ_PATH}/bin
export ICON_FILE=${PRJ_PATH}/qrscan.ico
export FINAL_PATH=QrScan

rm -rf ${WORK_PATH}
rm -rf ${DIST_PATH}

rm -f resources.py

${PRJ_PATH}/${PYTHON_NAME}/bin/pyrcc5 resources.qrc -o resources.py

${PYINSTALLER_FILE} --paths=${PYQT_PATH}  --specpath=${SPEC_PATH} --workpath=${WORK_PATH} --distpath=${DIST_PATH} --key "audYRD65jFDT87" --version-file ${PRJ_PATH}/file_version_info.txt --icon=${ICON_FILE} -D -w ${PRJ_PATH}/${PY_NAME}.py -y

mv ${DIST_PATH}/${PY_NAME} ${DIST_PATH}/${FINAL_PATH}

cp -r models ${DIST_PATH}/${FINAL_PATH}/

cd ${DIST_PATH}
zip -q -r ${FINAL_PATH}.zip ${FINAL_PATH}
mv ${FINAL_PATH}.zip ${PRJ_PATH}
cd ..
