#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: 'zfb'
# time: 2022-05-03 18:02

import logging

from os.path import isdir, normpath, exists
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QPlainTextEdit, QDialog, QGridLayout,
    QProgressBar, QPushButton, QRadioButton, QSizePolicy, QStyleFactory, 
    QFileDialog, QMessageBox, QLineEdit, QVBoxLayout, QHBoxLayout, QGroupBox)

from custom_formatter import CustomFormatter
from batch_work import BatchWork, scan_process
from os import makedirs, path
from datetime import datetime

from sql_helper import get_status, clean_files_table, clean_status_table
from utils import get_base_path

class QPlainTextEditLogger(QObject, logging.Handler):
    '''自定义Qt控件，继承自QObject，初始化时创建QPlainTextEdit控件\n
    用于实现QPlainTextEdit的日志输出功能
    '''
    # 信号量，负责实现外部进程更新UI进程的界面显示
    # UI进程的界面显示只能在UI主进程里面进行，所以这里触发信号，并传递参数
    # 前往信号对应的槽函数，进行处理
    # 该信号用于触发和传递日志信息
    new_record = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.new_record.emit(msg)


class QDropLineEdit(QLineEdit):
    '''用于实现拖放文件夹到编辑框的功能\n
    自定义Qt控件，继承自QLineEdit
    '''
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            files = [url.toLocalFile() for url in md.urls()]
            # 只接受文件夹的拖放
            files = [x for x in files if isdir(normpath(x))]
            num = len(files)
            if num > 1:
                logging.warning(f"检测到多条数据，只读取第一个！")
            elif num == 0:
                logging.warning(f"请确保拖放文件夹而不是文件！")
                return
            self.setText(files[0])
            event.acceptProposedAction()


class QrDetectDialog(QDialog):
    '''Qt界面的主窗体，继承自QDialog
    '''
    def __init__(self, parent=None):
        super(QrDetectDialog, self).__init__(parent)

        # 用于写入日志到QPlainTextEdit
        self.logger = QPlainTextEditLogger()
        logging.getLogger().addHandler(self.logger)
        # 设置日志的格式化类
        self.logger.setFormatter(CustomFormatter())
        # 设置日志的记录等级，低于该等级的日志将不会输出
        logging.getLogger().setLevel(logging.DEBUG)
        # 信号槽绑定，绑定在QPlainTextEditLogger创建的new_record信号到该函数
        self.logger.new_record.connect(self.logger.widget.appendHtml)
        self._loadThread = None
        self.run_func = None
        self.log_file = None

        # 界面基本元素创建
        self.createBottomLeftGroupBox()
        self.createTopLeftGroupBox()
        self.createControlGroupBox()
        self.createRightGroupBox(self.logger.widget)
        self.createProgressBar()

        # 用于在pyqt5中的一个线程中，开启多进程
        self.runButton.clicked.connect(self.batch_work)
        self.pauseButton.clicked.connect(self.pause_batch_work)
        self.resumeButton.clicked.connect(self.resume_batch_work)
        self.stopButton.clicked.connect(self.stop_batch_work)
        self.radioButton1.clicked.connect(self.disableCutPathStatus)
        self.radioButton2.clicked.connect(self.clickCutRadioButton)
        self.radioButton3.clicked.connect(self.clickDecodeRadioButton)
        self.imgPathButton.clicked.connect(self.get_img_path)
        self.cutPathButton.clicked.connect(self.get_cut_path)

        # 主界面布局搭建，网格布局
        mainLayout = QGridLayout()
        # addWidget(QWidget, row: int, column: int, rowSpan: int, columnSpan: int)
        mainLayout.addWidget(self.topLeftGroupBox, 1, 0)
        mainLayout.addWidget(self.bottomLeftGroupBox, 0, 0)
        mainLayout.addWidget(self.controlGroupBox, 2, 0)
        mainLayout.addWidget(self.rightGroupBox, 0, 1, 3, 1)
        mainLayout.addWidget(self.progressBar, 3, 0, 1, 2)
        # 设置每一列的宽度比例，第0列的宽度为1；第1列的宽度为2
        mainLayout.setColumnStretch(0, 1)
        mainLayout.setColumnStretch(1, 2)
        # 设置每一行的宽度比例，第0行的宽度为1；第1行的宽度为2
        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 1)
        mainLayout.setRowStretch(2, 2)
        self.setLayout(mainLayout)

        self.setWindowTitle("图片二维码检测识别 github.com/zfb132/QrScan")
        self.changeStyle('WindowsVista')
        self.load_exists()

    def load_exists(self):
        self.is_first = True
        res = get_status()
        if res:
            self.is_first = False
            # 弹窗询问是否继续上次的操作
            reply = QMessageBox.question(self, '提示', '检测到上次未完成的操作，是否继续？', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.No:
                clean_files_table()
                clean_status_table()
                return
            operation, img_path, cut_path = res
            if operation == "delete":
                self.radioButton1.setChecked(True)
                self.radioButton2.setChecked(False)
                self.radioButton3.setChecked(False)
            elif operation == "cut":
                self.radioButton2.setChecked(True)
                self.radioButton1.setChecked(False)
                self.radioButton3.setChecked(False)
            elif operation == "decode":
                self.radioButton3.setChecked(True)
                self.radioButton1.setChecked(False)
                self.radioButton2.setChecked(False)
            if img_path:
                self.imgPathTextBox.setText(img_path)
            if cut_path:
                self.cutPathTextBox.setText(cut_path)
            logging.info(f"上次未完成的操作为：{operation}")
            logging.info(f"图片路径为：{img_path}")
            logging.info(f"保存路径为：{cut_path}")


    def set_run_func(self, func):
        self.run_func = func
    
    def get_img_path(self):
        directory = QFileDialog.getExistingDirectory(self, "选取图片所在的文件夹")
        self.imgPathTextBox.setText(directory)

    def get_cut_path(self):
        directory = QFileDialog.getExistingDirectory(self, "选取保存结果的文件夹")
        self.cutPathTextBox.setText(directory)

    def set_log_file(self):
        log_name = path.join(get_base_path(), "log", f"{datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
        try:
            self.log_file = open(log_name, "w", encoding="utf-8")
            logging.info(f"日志文件{log_name}创建成功")
        except Exception as e:
            logging.warning(f"日志文件{log_name}创建失败")
            logging.warning(repr(e))

    def batch_work(self):
        # 运行按钮的响应函数
        # 获取操作类型，cut还是delete
        operation = 'cut'
        if self.radioButton1.isChecked():
            operation = 'delete'
        if self.radioButton2.isChecked():
            operation = 'cut'
        if self.radioButton3.isChecked():
            operation = 'decode'
        c1 = self.imgPathTextBox.text().strip()
        if not c1:
            QMessageBox.warning(self, '警告', f'请先设置图片所在文件夹！', QMessageBox.Yes)
            return
        # 保证路径都是标准格式
        img_path = normpath(c1)
        if not exists(img_path):
            QMessageBox.warning(self, '警告', f'不存在路径：{img_path}', QMessageBox.Yes)
            return
        cut_path = ""
        if operation != 'delete':
            c2 = self.cutPathTextBox.text().strip()
            if not c2:
                msg = "请先设置保存二维码图片的文件夹！"
                if operation == 'decode':
                    msg = "请先设置保存二维码识别结果的文件夹！"
                QMessageBox.warning(self, '警告', f'{msg}', QMessageBox.Yes)
                return
            cut_path = normpath(c2)
            if not exists(cut_path):
                QMessageBox.warning(self, '警告', f'不存在路径：{img_path}', QMessageBox.Yes)
                return
        # 设置默认日志
        self.logger.widget.setPlainText("")
        logging.critical("作者：zfb")
        logging.critical("https://github.com/zfb132/QrScan")
        # 创建线程
        self._loadThread=QThread(parent=self)
        self.set_log_file()
        # vars = [1, 2, 3, 4, 5, 6]*6
        vars = [img_path, cut_path, operation, self.log_file, self.is_first]
        self.loadThread=BatchWork(vars, self.run_func)
        # 为BatchWork类的两个信号绑定槽函数
        self.loadThread.notifyProgress.connect(self.updateProgressBar)
        self.loadThread.notifyStatus.connect(self.updateButtonStatus)
        # 用于开辟新进程，不阻塞主界面
        self.loadThread.moveToThread(self._loadThread)
        self._loadThread.started.connect(self.loadThread.run)
        self._loadThread.start()

    def pause_batch_work(self):
        if self.loadThread:
            self.loadThread.event.clear()
            logging.critical("暂停运行！")
        self.resumeButton.setDisabled(False)
        self.pauseButton.setDisabled(True)

    def resume_batch_work(self):
        if self.loadThread:
            self.loadThread.event.set()
            logging.critical("继续运行！")
        self.resumeButton.setDisabled(True)
        self.pauseButton.setDisabled(False)

    def stop_batch_work(self):
        if self.loadThread:
            self.loadThread.pool.terminate()
            self.loadThread.pool.join()
            logging.critical("手动停止运行！")
        self.runButton.setDisabled(False)
        self.pauseButton.setDisabled(True)
        self.resumeButton.setDisabled(True)
        self.stopButton.setDisabled(True)
        # if self._loadThread:
        #     self._loadThread.quit()
        #     self._loadThread.wait()
        #     self.imgPathTextBox.setText("AA")

    def changeStyle(self, styleName):
        QApplication.setStyle(QStyleFactory.create(styleName))
        self.changePalette()

    def changePalette(self):
        QApplication.setPalette(QApplication.style().standardPalette())

    def updateProgressBar(self, i):
        self.progressBar.setValue(i)
    
    def updateButtonStatus(self, status):
        self.runButton.setDisabled(status)
        self.pauseButton.setDisabled(not status)
        self.resumeButton.setDisabled(True)
        self.stopButton.setDisabled(not status)
        if not status:
            QMessageBox.information(self, '提示', '成功完成扫描！', QMessageBox.Yes)
    
    def disableCutPathStatus(self):
        self.cutPathButton.setDisabled(True)
        self.cutPathTextBox.setDisabled(True)
    
    def clickCutRadioButton(self):
        self.cutPathButton.setDisabled(False)
        self.cutPathTextBox.setDisabled(False)
        self.cutPathButton.setText("选择剪切图片文件夹")
    
    def clickDecodeRadioButton(self):
        self.cutPathButton.setDisabled(False)
        self.cutPathTextBox.setDisabled(False)
        self.cutPathButton.setText("选择保存二维码识别结果文件夹")

    def createBottomLeftGroupBox(self):
        self.bottomLeftGroupBox = QGroupBox("包含二维码的图片操作")

        self.radioButton1 = QRadioButton("删除")
        self.radioButton2 = QRadioButton("剪切")
        self.radioButton3 = QRadioButton("识别")
        self.radioButton2.setChecked(True)

        layout = QGridLayout()
        layout.addWidget(self.radioButton1,0,0,1,1)
        layout.addWidget(self.radioButton2,1,0,1,1)
        layout.addWidget(self.radioButton3,0,1,1,1)
        #layout.addStretch(1)
        self.bottomLeftGroupBox.setLayout(layout)

    def createTopLeftGroupBox(self):
        self.topLeftGroupBox = QGroupBox("设置路径")

        self.imgPathButton = QPushButton("选择原始图片文件夹")
        self.imgPathButton.setDefault(True)

        self.imgPathTextBox = QDropLineEdit("")
        self.cutPathTextBox = QDropLineEdit("")

        self.cutPathButton = QPushButton("选择剪切图片文件夹")
        self.cutPathButton.setDefault(True)

        layout = QVBoxLayout()
        layout.addWidget(self.imgPathButton)
        layout.addWidget(self.imgPathTextBox)
        layout.addWidget(self.cutPathButton)
        layout.addWidget(self.cutPathTextBox)
        
        self.topLeftGroupBox.setLayout(layout)

    def createControlGroupBox(self):
        self.controlGroupBox = QGroupBox("控制按钮")
        layout = QGridLayout()
        self.runButton = QPushButton("启动")
        self.runButton.setDefault(True)
        self.pauseButton = QPushButton("暂停")
        self.pauseButton.setDefault(False)
        self.pauseButton.setDisabled(True)
        self.resumeButton = QPushButton("继续")
        self.resumeButton.setDefault(False)
        self.resumeButton.setDisabled(True)
        self.stopButton = QPushButton("停止")
        self.stopButton.setDefault(False)
        self.stopButton.setDisabled(True)
        layout.addWidget(self.runButton, 0, 0)
        layout.addWidget(self.pauseButton, 0, 1)
        layout.addWidget(self.resumeButton, 1, 0)
        layout.addWidget(self.stopButton, 1, 1)
        self.controlGroupBox.setLayout(layout)

    def createRightGroupBox(self, widget):
        self.rightGroupBox = QGroupBox("运行日志")
        layout = QHBoxLayout()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        widget.setMaximumBlockCount(10000)
        widget.setPlainText("作者：zfb\nhttps://github.com/zfb132/QrScan")
        layout.addWidget(widget)
        #layout.addStretch(0)
        self.rightGroupBox.setLayout(layout)

    def createProgressBar(self):
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)