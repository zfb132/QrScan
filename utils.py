#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: 'zfb'
# time: 2023-12-25 18:26

import sys
# from os import getcwd
from os.path import dirname, abspath

def get_base_path():
    """
    获取当前运行目录，适应于Python和PyInstaller环境
    """
    # path = getcwd()
    path = dirname(abspath(__file__))
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 如果是PyInstaller环境
        # 可以使用 sys.executable 获取当前运行的exe路径
        # 也可以使用 sys._MEIPASS 获取当前运行的exe所在目录下的_internal文件夹的路径
        #   例如 D:\QrScan\bin\QrScan\_internal
        # 获取 _internal 文件夹的路径，然后使用 dirname 获取上一级目录
        path = dirname(sys._MEIPASS)
    return path