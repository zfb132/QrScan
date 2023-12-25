#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: 'zfb'
# time: 2022-02-20 11:18

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from multiprocessing import freeze_support
import sys
import os
import logging

from custom_qwidget import QrDetectDialog, scan_process
from sql_helper import create_files_table, create_status_table
from utils import get_base_path

# 用于把图片资源嵌入到Qt程序里面
# 发布exe时就不需要附该文件了
import resources

def log_init():
    try:
        # 当前程序的路径
        log_dir = os.path.join(get_base_path(), "log")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            logging.info(f"日志文件夹{log_dir}创建成功")
        else:
            logging.info(f"日志文件夹{log_dir}已存在")
    except Exception as e:
        logging.warning(f"日志文件{log_dir}创建失败")
        logging.warning(repr(e))

if __name__ == '__main__':
    # 如果用pyinstaller打包含有多进程的代码，这一行必须要
    # 且在最开始执行
    freeze_support()
    create_files_table()
    create_status_table()
    app = QApplication(sys.argv)
    detectDialog = QrDetectDialog()
    detectDialog.set_run_func(scan_process)
    detectDialog.setWindowFlags(Qt.WindowMinimizeButtonHint|Qt.WindowCloseButtonHint)
    detectDialog.setWindowIcon(QIcon(':/icons/icon.png'))
    screen = app.desktop()
    detectDialog.resize(screen.height(),screen.height()//2)
    fg = detectDialog.frameGeometry()
    sc = screen.availableGeometry().center()
    fg.moveCenter(sc)
    detectDialog.show()
    log_init()
    code = app.exec_()
    if detectDialog._loadThread:
        detectDialog._loadThread.quit()
    sys.exit(code)