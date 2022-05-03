from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QSizePolicy, QStyleFactory, QVBoxLayout, 
        QPlainTextEdit, QFileDialog, QMessageBox)
from PyQt5.QtGui import QColor, QIcon

from multiprocessing import freeze_support, cpu_count, Pool
import sys
import os
import random
import logging
from datetime import datetime
from cv2 import imdecode, IMREAD_UNCHANGED, wechat_qrcode_WeChatQRCode
from numpy import fromfile, uint8
from shutil import move

# 用于把图片资源嵌入到Qt程序里面
# 发布exe时就不需要附该文件了
import resources


try:
    # 使用opencv的wechat_qrcode模块创建二维码识别器
    detector = wechat_qrcode_WeChatQRCode(
        "models/detect.prototxt", "models/detect.caffemodel", 
        "models/sr.prototxt", "models/sr.caffemodel"
    )
    # print("创建识别器成功")
except:
    print("初始化识别器失败！")
    exit(0)


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


class BatchWork(QObject):
    '''具体的多进程工作处理的类，通过构造函数接收参数和任务处理的函数
    '''
    # 信号量，负责实现外部进程更新UI进程的界面显示
    # UI进程的界面显示只能在UI主进程里面进行，所以这里触发信号，并传递参数
    # 前往信号对应的槽函数，进行处理
    # 该信号用于触发和传递任务的执行进度（并非实时，只能每批任务执行完毕，统一更新）
    notifyProgress = pyqtSignal(int)
    # 该信号用于指示目前的工作状态，控制按钮的启用与否（保证任务运行过程中不会再次运行）
    notifyStatus = pyqtSignal(bool)

    def __init__(self, myvar, func):
        '''通过构造函数的myvar变量接收参数\n
        通过func函数接收具体用于任务处理的函数
        '''
        self.work = func
        self.var = myvar
        super(BatchWork, self).__init__()
    
    def chunks(self, l, n):
        '''此函数用于配合实现列表分割
        '''
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def resize_list(self, data_list, group_size):
        '''将一维列表按照指定长度分割
        '''
        data_chunks = list(self.chunks(data_list, group_size))
        results = []
        for i in range(len(data_chunks)):
            results.append(data_chunks[i])
        return results
    
    def show_info(self, img_status, op_status, name):
        '''根据返回的状态码显示不同的日志内容
        '''
        if img_status is None:
            logging.error(f"{name}出现未知错误！")
            return
        elif img_status == 1:
            logging.debug(f"{name}检测到二维码")
        elif img_status == 2:
            logging.info(f"{name}不包含二维码")
        elif img_status == 3:
            logging.warning(f"{name}不是一个合法图片！")
            return
        elif img_status == 4:
            logging.warning(f"{name}不是一个图片！")
            return
        else:
            logging.error(f"{name}程序出现bug！")
            return
        if op_status is None:
            logging.error(f"{name}出现未知错误！")
        elif op_status == 1:
            logging.debug(f"{name}剪切成功")
        elif op_status == 2:
            logging.error(f"{name}剪切失败！")
        elif op_status == 3:
            logging.debug(f"{name}删除成功")
        elif op_status == 4:
            logging.error(f"{name}删除失败！")
        elif op_status == 5:
            logging.debug(f"{name}重名，添加时间戳后剪切成功")
        elif op_status == 6:
            logging.error(f"{name}重名，添加时间戳后剪切仍然失败！")
        elif op_status == 7:
            pass
        else:
            logging.error(f"{name}程序出现bug！")

    def run(self):
        # 使用信号槽机制，禁用按钮，因为此时已经开始处理
        # 防止用户再次提交任务
        self.notifyStatus.emit(True)
        logging.info('开始进行检测')
        # 读取参数
        path, cut_path, operation = self.var
        # 传入的path和cut_path已经是normpath
        # path = os.path.normpath(path)
        # 读取path及其子目录下的所有文件（所有扩展名）并存入m*2*n列表
        pathes = []
        for root, dirs, files in os.walk(path):
            # for dir_name in dirs:
            #    rename_func(root, dir_name)
            for file_name in files:
                pathes.append([root, file_name])
        logging.info(f"载入所有{len(pathes)}个文件成功！")
        # 根据CPU核心数量开启多进程，充分利用资源
        pro_cnt = cpu_count()
        # 按照每组100个进行分割
        # group_size = 100
        # if len(pathes) < 1000:
        #     group_size = len(pathes)//(2*pro_cnt)
        # if group_size < 1:
        #     group_size = 1
        # 还是默认4个吧，否则一个批次的任务执行时间太久，日志和进度条会好久才动
        group_size = 4
        # 把m*2*n的列表分割成新列表，新列表的前面t-1元素都是group_size*2*n
        # 最后一个元素[len(pathes)-(t-1)*group_size]X2Xn
        final_pathes = self.resize_list(pathes, group_size)
        # 最终创建进程的数量（一般远大于进程池的大小）
        num_procs = len(final_pathes)
        # 用于存放多进程返回结果的列表
        results = list(range(num_procs))
        # 创建进程池
        pool = Pool(processes=pro_cnt)
        # 开始逐个将进程加入进程池
        for i in range(num_procs):
            params = final_pathes[i]
            # 维持执行的进程总数为processes，当一个进程执行完毕后会添加新的进程进去
            results[i] = pool.apply_async(func=self.work, args=(params, cut_path, operation,))
        logging.info(f"创建{num_procs}个进程，进程池大小：{pro_cnt}")
        pool.close()
        # 调用join之前，先调用close函数，否则会出错。
        # 执行完close后不会有新的进程加入到pool，join函数等待所有子进程结束
        # pool.join()
        # 用于统计含有二维码图片的数量
        qr_img_num = 0
        # 用于统计操作成功的次数（包含剪切成功、删除成功、添加时间戳后剪切成功）
        op_success_num = 0
        for i in range(len(results)):
            # 每个批次执行完毕才会进来
            m = results[i].get()
            # 格式化输出结果
            for t in range(len(m)):
                name = os.path.join(final_pathes[i][t][0], final_pathes[i][t][1])
                img_status, op_status = m[t]
                if img_status == 1:
                    qr_img_num += 1
                # 剪切成功、删除成功、添加时间戳后剪切成功
                if op_status in [1,3,5]:
                    op_success_num += 1
                # 显示每个批次的日志
                self.show_info(img_status, op_status, name)
            # 更新进度条（进度条的上限初始化为100）
            self.notifyProgress.emit((i+1)*100//num_procs)
            # logging.info(f"进程{i}结束")
        logging.info(f"扫描任务结束：")
        logging.info(f"共计检测到{qr_img_num}个包含二维码的图片，其中{op_success_num}个文件执行操作成功")
        # 使用信号槽机制，启用按钮，因为任务已经处理完成
        # 用户可以再次提交任务或创建新任务
        self.notifyStatus.emit(False)


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
            files = [x for x in files if os.path.isdir(os.path.normpath(x))]
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

        # 界面基本元素创建
        self.createBottomLeftGroupBox()
        self.createTopLeftGroupBox()
        self.createRightGroupBox(self.logger.widget)
        self.createProgressBar()

        # 用于在pyqt5中的一个线程中，开启多进程
        self.runButton.clicked.connect(self.batch_work)
        self.radioButton1.clicked.connect(self.disableCutPathStatus)
        self.radioButton2.clicked.connect(self.enableCutPathStatus)
        self.imgPathButton.clicked.connect(self.get_img_path)
        self.cutPathButton.clicked.connect(self.get_cut_path)

        # 主界面布局搭建，网格布局
        mainLayout = QGridLayout()
        # addWidget(QWidget, row: int, column: int, rowSpan: int, columnSpan: int)
        mainLayout.addWidget(self.topLeftGroupBox, 1, 0)
        mainLayout.addWidget(self.bottomLeftGroupBox, 0, 0)
        mainLayout.addWidget(self.rightGroupBox, 0, 1, 2, 1)
        mainLayout.addWidget(self.progressBar, 2, 0, 1, 2)
        # 设置每一列的宽度比例，第0列的宽度为1；第1列的宽度为2
        mainLayout.setColumnStretch(0, 1)
        mainLayout.setColumnStretch(1, 2)
        # 设置每一行的宽度比例，第0行的宽度为1；第1行的宽度为2
        mainLayout.setRowStretch(0, 1)
        mainLayout.setRowStretch(1, 2)
        self.setLayout(mainLayout)

        self.setWindowTitle("图片二维码检测 github.com/zfb132/QrScan")
        self.changeStyle('WindowsVista')

    
    def get_img_path(self):
        directory = QFileDialog.getExistingDirectory(self, "选取图片所在的文件夹")
        self.imgPathTextBox.setText(directory)

    def get_cut_path(self):
        directory = QFileDialog.getExistingDirectory(self, "选取包含二维码的图片存放的文件夹")
        self.cutPathTextBox.setText(directory)

    def batch_work(self):
        # 运行按钮的响应函数
        # 获取操作类型，cut还是delete
        operation = 'cut'
        if self.radioButton1.isChecked() and not self.radioButton2.isChecked():
            operation = 'delete'
        c1 = self.imgPathTextBox.text()
        if not c1:
            QMessageBox.warning(self, '警告', f'请先设置图片所在文件夹！', QMessageBox.Yes)
            return
        c2 = self.cutPathTextBox.text()
        if not c2 and operation == 'cut':
            QMessageBox.warning(self, '警告', f'请先设置保存二维码图片的文件夹！', QMessageBox.Yes)
            return
        # 保证路径都是标准格式
        img_path = os.path.normpath(c1)
        cut_path = os.path.normpath(c2)
        if not os.path.exists(img_path):
            QMessageBox.warning(self, '警告', f'不存在路径：{img_path}', QMessageBox.Yes)
            return
        if not os.path.exists(cut_path) and operation == 'cut':
            QMessageBox.warning(self, '警告', f'不存在路径：{img_path}', QMessageBox.Yes)
            return
        # 设置默认日志
        self.logger.widget.setPlainText("作者：zfb\nhttps://github.com/zfb132/QrScan")
        # 创建线程
        self._loadThread=QThread(parent=self)
        # vars = [1, 2, 3, 4, 5, 6]*6
        vars = [img_path, cut_path, operation]
        self.loadThread=BatchWork(vars, scan_process)
        # 为BatchWork类的两个信号绑定槽函数
        self.loadThread.notifyProgress.connect(self.updateProgressBar)
        self.loadThread.notifyStatus.connect(self.updateButtonStatus)
        # 用于开辟新进程，不阻塞主界面
        self.loadThread.moveToThread(self._loadThread)
        self._loadThread.started.connect(self.loadThread.run)
        self._loadThread.start()

    def changeStyle(self, styleName):
        QApplication.setStyle(QStyleFactory.create(styleName))
        self.changePalette()

    def changePalette(self):
        QApplication.setPalette(QApplication.style().standardPalette())

    def updateProgressBar(self, i):
        self.progressBar.setValue(i)
    
    def updateButtonStatus(self, status):
        self.runButton.setDisabled(status)
    
    def disableCutPathStatus(self):
        self.cutPathButton.setDisabled(True)
        self.cutPathTextBox.setDisabled(True)
    
    def enableCutPathStatus(self):
        self.cutPathButton.setDisabled(False)
        self.cutPathTextBox.setDisabled(False)

    def createBottomLeftGroupBox(self):
        self.bottomLeftGroupBox = QGroupBox("包含二维码的图片操作")

        self.radioButton1 = QRadioButton("删除")
        self.radioButton2 = QRadioButton("剪切")
        self.radioButton2.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(self.radioButton1)
        layout.addWidget(self.radioButton2)
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

        self.runButton = QPushButton("一键运行检测")
        self.runButton.setDefault(True)

        layout = QVBoxLayout()
        layout.addWidget(self.imgPathButton)
        layout.addWidget(self.imgPathTextBox)
        layout.addWidget(self.cutPathButton)
        layout.addWidget(self.cutPathTextBox)
        layout.addStretch(1)
        layout.addWidget(self.runButton)
        
        self.topLeftGroupBox.setLayout(layout)

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


def work(fn):
    print(f"run {fn}\n")
    a = []
    for i in range(10000000):
        a.append(random.random())
    print(f"finish {fn}\n")
    return datetime.now().strftime("%Y%m%d%H%M%S")


def scan(root, name, cut_path, operation):
    '''
    @param root 图片文件的路径
    @param name 图片文件的名称
    @param cut_path 准备存放包含二维码图片的路径
    @operation 对包含二维码的图片要进行的操作。'cut'表示剪切到cut_path文件夹，'delete'表示删除该图片
    @return [img_status, op_status]

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
    '''
    img_status = None
    op_status = None
    img_name = os.path.join(root, name)
    # imread不支持中文路径
    # img = imread(img_name)
    npfile = fromfile(img_name, dtype=uint8)
    if npfile.size == 0:
        logging.error(f"{img_name} 是空文件！")
        return [4, op_status]
    img = imdecode(npfile, IMREAD_UNCHANGED)
    if img is None:
        logging.warning(f"{img_name} 不是一个图片！")
        return [4, op_status]
    # if img.empty():
    if img.size == 0 :
        logging.error(f"{img_name} 不是一个合法图片！")
        return [3, None]
    try:
        res, points = detector.detectAndDecode(img)
    except Exception as e:
        print(repr(e))
        return [None, None]
    if res == None or len(res) < 1:
        logging.info(f"{img_name} 不包含二维码")
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
                    logging.debug(f"{img_name}--->{new_name}")
                    op_status = 1
                else:
                    file_exist = True
                    logging.warning(f"文件{img_name}已存在！")
            except Exception as e:
                logging.error(repr(e))
                logging.error(f"剪切文件{img_name}失败！")
                op_status = 2
            if file_exist:
                from datetime import datetime
                time_str = datetime.now().strftime("_%Y%m%d%H%M%S")
                m = os.path.splitext(new_name)
                new_name = m[0] + time_str + m[1]
                try:
                    move(img_name, new_name)
                    logging.debug(f"{img_name}--->{new_name}")
                    op_status = 5
                except Exception as e:
                    logging.error(repr(e))
                    logging.error(f"剪切文件{img_name}失败！")
                    op_status = 6
        elif operation == 'delete':
            try:
                os.remove(img_name)
                logging.debug(f"已删除文件{img_name}")
                op_status = 3
            except Exception as e:
                logging.error(repr(e))
                logging.error(f"删除文件{img_name}失败！")
                op_status = 4
    return [img_status, op_status]


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
    detectDialog.setWindowFlags(Qt.WindowMinimizeButtonHint|Qt.WindowCloseButtonHint)
    detectDialog.setWindowIcon(QIcon(':/icons/icon.png'))
    screen = app.desktop()
    detectDialog.resize(screen.height(),screen.height()//2)
    fg = detectDialog.frameGeometry()
    sc = screen.availableGeometry().center()
    fg.moveCenter(sc)
    detectDialog.show()
    code = app.exec_()
    if detectDialog._loadThread:
        detectDialog._loadThread.quit()
    sys.exit(code)