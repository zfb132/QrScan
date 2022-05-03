#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: 'zfb'
# time: 2022-05-03 18:02

import logging

from PyQt5.QtGui import QColor

class CustomFormatter(logging.Formatter):
    '''自定义日志的格式化，保证QPlainTextEdit可以用不同颜色显示对应等级的日志
    '''
    # 定义不同日志等级的格式和颜色
    FORMATS = {
        logging.ERROR:   ("[{asctime}] {levelname:-<8}--- {message}", QColor("red")),
        logging.DEBUG:   ("[{asctime}] {levelname:-<8}--- {message}", "green"),
        logging.INFO:    ("[{asctime}] {levelname:-<8}--- {message}", "#0000FF"),
        logging.WARNING: ('[{asctime}] {levelname:-<8}--- {message}', QColor(100, 100, 0))
    }

    def __init__(self):
        '''把格式化设置为{}风格，而不是()%s，从子类修改父类
        '''
        super().__init__(style="{")

    def format(self, record):
        '''继承logging.Formatter必须实现的方法
        '''
        last_fmt = self._style._fmt
        opt = CustomFormatter.FORMATS.get(record.levelno)
        # 设置时间日期的格式化规则
        self.datefmt = "%Y-%m-%d %H:%M:%S"
        if opt:
            fmt, color = opt
            self._style._fmt = "<font color=\"{}\">{}</font>".format(QColor(color).name(),fmt)
        res = logging.Formatter.format(self, record)
        self._style._fmt = last_fmt
        return res