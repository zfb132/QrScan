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
from datetime import datetime
from cv2 import imdecode, IMREAD_UNCHANGED, wechat_qrcode_WeChatQRCode
from numpy import fromfile, uint8
from shutil import move

from custom_qwidget import QrDetectDialog

# 用于把图片资源嵌入到Qt程序里面
# 发布exe时就不需要附该文件了
import resources

try:
    # 使用opencv的wechat_qrcode模块创建二维码识别器
    # https://github.com/WeChatCV/opencv_3rdparty/tree/wechat_qrcode
    detector = wechat_qrcode_WeChatQRCode(
        "models/detect.prototxt", "models/detect.caffemodel", 
        "models/sr.prototxt", "models/sr.caffemodel"
    )
    # print("创建识别器成功")
except:
    print("初始化识别器失败！")
    exit(0)

def log_init():
    try:
        # 当前程序的路径
        log_dir = os.path.join(os.path.dirname(__file__), "log")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            logging.info(f"日志文件夹{log_dir}创建成功")
        else:
            logging.info(f"日志文件夹{log_dir}已存在")
    except Exception as e:
        logging.warning(f"日志文件{log_dir}创建失败")
        logging.warning(repr(e))

def scan(root, name, cut_path, operation):
    '''
    @param root 图片文件的路径
    @param name 图片文件的名称
    @param cut_path 准备存放包含二维码图片的路径
    @operation 对包含二维码的图片要进行的操作。
        'cut'表示剪切到cut_path文件夹，'delete'表示删除该图片，'decode'表示识别二维码
    @return [img_status, op_status, qrcode]

    img_status:
        None表示遇到未知问题
        1表示输入文件是包含二维码的图片\n
        2表示输入文件是不包含二维码的图片\n
        3表示输入文件不是一个合法图片\n
        4表示输入文件不是一个图片\n
    
    op_status:
        None表示遇到未知问题
        1表示文件剪切成功
        2表示文件剪切失败
        3表示文件删除成功
        4表示文件删除失败
        5表示文件已有重名，添加时间戳后剪切成功
        6表示文件有重名，且添加时间戳后也失败
        7表示对文件不进行任何操作
        8表示文件识别成功
    '''
    img_status = None
    op_status = None
    # [图片名称, [二维码]]
    qrcode = None
    # 处理过程中的运行信息
    note = None
    img_name = os.path.join(root, name)
    # imread不支持中文路径
    # img = imread(img_name)
    npfile = fromfile(img_name, dtype=uint8)
    if npfile.size == 0:
        note = f"空白文件: {img_name}"
        logging.error(note)
        return [4, op_status, qrcode, note]
    img = imdecode(npfile, IMREAD_UNCHANGED)
    if img is None:
        note = f"不是图片: {img_name}"
        logging.warning(note)
        return [4, op_status, qrcode, note]
    # if img.empty():
    if img.size == 0 :
        note = f"非法图片: {img_name} 不是一个合法图片！"
        logging.error(note)
        return [3, op_status, qrcode, note]
    try:
        res, points = detector.detectAndDecode(img)
    except Exception as e:
        print(repr(e))
        note = f"未知文件: {img_name} 识别失败！"
        return [None, op_status, qrcode, note]
    if res == None or len(res) < 1:
        note = f"无二维码: {img_name}"
        logging.info(note)
        img_status = 2
        op_status = 7
    else:
        logging.debug(f"{img_name} 检测到二维码")
        img_status = 1
        if operation == 'cut':
            new_name = os.path.join(cut_path, name)
            file_exist = False
            try:
                if not os.path.exists(new_name):
                    move(img_name, new_name)
                    note = f"直接剪切: {img_name}--->{new_name}"
                    logging.debug(note)
                    op_status = 1
                else:
                    file_exist = True
                    logging.warning(f"文件{img_name}已存在！")
            except Exception as e:
                logging.error(repr(e))
                note = f"剪切失败: {img_name} 直接剪切失败！"
                logging.error(note)
                op_status = 2
            if file_exist:
                time_str = datetime.now().strftime("_%Y%m%d%H%M%S%f")
                m = os.path.splitext(new_name)
                new_name = m[0] + time_str + m[1]
                try:
                    move(img_name, new_name)
                    note = f"重名剪切: {img_name}--->{new_name}"
                    logging.debug(note)
                    op_status = 5
                except Exception as e:
                    logging.error(repr(e))
                    note = f"剪切失败: {img_name} 重命名后剪切失败！"
                    logging.error(note)
                    op_status = 6
        elif operation == 'delete':
            try:
                os.remove(img_name)
                note = f"删除成功: {img_name}"
                logging.debug(note)
                op_status = 3
            except Exception as e:
                logging.error(repr(e))
                note = f"删除失败: {img_name}"
                logging.error(note)
                op_status = 4
        elif operation == 'decode':
            op_status = 8
            note = f"识别成功: {img_name}"
        full_name = os.path.normpath(img_name)
        qrcode = [full_name, res]
    return [img_status, op_status, qrcode, note]


def scan_process(pathes, cut_path, operation):
    '''批次任务启动过程中的中转函数
    '''
    results = []
    for path in pathes:
        results.append(scan(path[0], path[1], cut_path, operation))
    return results


if __name__ == '__main__':
    # 如果用pyinstaller打包含有多进程的代码，这一行必须要
    # 且在最开始执行
    freeze_support()
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