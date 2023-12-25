#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: 'zfb'
# time: 2022-05-03 18:02

import logging
from datetime import datetime
from cv2 import imdecode, cvtColor, IMREAD_UNCHANGED, COLOR_GRAY2RGB, COLOR_RGBA2RGB, wechat_qrcode_WeChatQRCode
from numpy import fromfile, uint8, uint16
from shutil import move
from sys import exit

from multiprocessing import Event, cpu_count, Pool
from os.path import join, dirname, basename, exists, splitext, normpath
from os import walk, remove
from PyQt5.QtCore import QObject, pyqtSignal

from sql_helper import insert_file, insert_status, clean_files_table, clean_status_table, get_all_files
from utils import get_base_path

def setup_event(event):
    global unpaused
    unpaused = event

try:
    # 使用opencv的wechat_qrcode模块创建二维码识别器
    # https://github.com/WeChatCV/opencv_3rdparty/tree/wechat_qrcode
    model_base_path = join(get_base_path(), "models")
    detector = wechat_qrcode_WeChatQRCode(
        join(model_base_path, "detect.prototxt"), join(model_base_path, "detect.caffemodel"), 
        join(model_base_path, "sr.prototxt"), join(model_base_path, "sr.caffemodel")
    )
    # print("创建识别器成功")
except Exception as e:
    print(repr(e))
    print("初始化识别器失败！")
    exit(0)

def convert_to_8bit_rgb(img):
    """
    将图像转换为8位RGB格式。
    如果图像已经是8位RGB，则不进行任何操作。
    """
    # 如果图像是灰度图，转换为RGB
    if len(img.shape) == 2:
        img = cvtColor(img, COLOR_GRAY2RGB)

    # 如果图像是16位深度，转换为8位
    elif img.dtype == uint16:
        img = (img / 256).astype(uint8)

    # 如果图像是RGBA，转换为RGB
    elif img.shape[2] == 4:
        img = cvtColor(img, COLOR_RGBA2RGB)

    return img

def scan(img_name, cut_path, operation):
    '''
    @param img_name 图片文件的名称
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
    full_name = img_name
    # imread不支持中文路径
    # img = imread(img_name)
    npfile = fromfile(img_name, dtype=uint8)
    if npfile.size == 0:
        note = f"空白文件: {img_name}"
        logging.error(note)
        return [4, op_status, [full_name, qrcode], note]
    img = imdecode(npfile, IMREAD_UNCHANGED)
    if img is None:
        note = f"不是图片: {img_name}"
        logging.warning(note)
        return [4, op_status, [full_name, qrcode], note]
    # if img.empty():
    if img.size == 0 :
        note = f"空白图片: {img_name} 不是一个合法图片！"
        logging.error(note)
        return [3, op_status, [full_name, qrcode], note]
    try:
        img = convert_to_8bit_rgb(img)
        res, points = detector.detectAndDecode(img)
    except Exception as e:
        print(repr(e))
        note = f"识别失败: {img_name} 识别失败！"
        return [None, op_status, [full_name, qrcode], note]
    # res=None  res=() res=("")
    if res == None or len(res) < 1 or (len(res) == 1 and not res[0]):
        note = f"无二维码: {img_name}"
        logging.info(note)
        img_status = 2
        op_status = 7
        return [img_status, op_status, [full_name, qrcode], note]
    else:
        logging.debug(f"{img_name} 检测到二维码")
        img_status = 1
        if operation == 'cut':
            new_name = join(cut_path, basename(img_name))
            file_exist = False
            try:
                if not exists(new_name):
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
                m = splitext(new_name)
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
                remove(img_name)
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
        qrcode = [full_name, res]
    return [img_status, op_status, qrcode, note]


def scan_process(pathes, cut_path, operation):
    '''批次任务启动过程中的中转函数
    '''
    results = []
    for path in pathes:
        unpaused.wait()
        results.append(scan(path, cut_path, operation))
    return results

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
        self.var = myvar[:3]
        self.log_file = myvar[3]
        self.is_first = myvar[4]
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
        elif op_status == 8:
            logging.debug(f"{name}识别二维码成功")
        else:
            logging.error(f"{name}程序出现bug！")

    def save_qrcode(self, path, qrcode, is_log=False):
        if is_log:
            pure_log_name = basename(self.log_file.name).split('.')[:-1]
            name = join(path, f"{'.'.join(pure_log_name)}.csv")
        else:
            name = join(path, "qrcode.csv")
        flag = False
        with open(name, "a", encoding="utf-8-sig", errors="replace") as f:
            for single_res in qrcode:
                if single_res is None:
                    continue
                f.write(f'"{single_res[0]}",{",".join(single_res[1])}\n')
                flag = True
            if flag:
                logging.debug(f"识别二维码结果保存到文件{name}成功！")

    def filter_names(self, pathes):
        '''
        从数据库中读取已经识别过的文件，将其从pathes中删除
        '''
        db_normpath_names = [x[0] for x in get_all_files()]
        # item in new_lists but not in db_normpath_names
        return list(set(pathes) - set(db_normpath_names))

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
        for root, dirs, files in walk(path):
            # for dir_name in dirs:
            #    rename_func(root, dir_name)
            for file_name in files:
                pathes.append(normpath(join(root, file_name)))
        if not self.is_first:
            logging.info("检测到上次运行未结束，将过滤已经识别过的文件")
            pathes = self.filter_names(pathes)
        logging.info(f"载入所有{len(pathes)}个文件成功！")
        # 根据CPU核心数量开启多进程，充分利用资源
        pro_cnt = cpu_count()
        # 按照每组100个进行分割
        # group_size = 100
        # if len(pathes) < 1000:
        #     group_size = len(pathes)//(2*pro_cnt)
        # if group_size < 1:
        #     group_size = 1
        # 还是默认8个吧，否则一个批次的任务执行时间太久，日志和进度条会好久才动
        group_size = 4
        # 把m*2*n的列表分割成新列表，新列表的前面t-1元素都是group_size*2*n
        # 最后一个元素[len(pathes)-(t-1)*group_size]X2Xn
        final_pathes = self.resize_list(pathes, group_size)
        # 最终创建进程的数量（一般远大于进程池的大小）
        num_procs = len(final_pathes)
        # 用于存放多进程返回结果的列表
        results = list(range(num_procs))
        insert_status(operation, path, cut_path, 0)
        # 创建进程池
        self.event = Event()
        self.pool = Pool(processes=pro_cnt, initializer=setup_event, initargs=(self.event,))
        # 开始逐个将进程加入进程池
        for i in range(num_procs):
            params = final_pathes[i]
            # 维持执行的进程总数为processes，当一个进程执行完毕后会添加新的进程进去
            results[i] = self.pool.apply_async(func=self.work, args=(params, cut_path, operation,))
        logging.info(f"创建{num_procs}个进程，进程池大小：{pro_cnt}")
        self.pool.close()
        # unpause workers
        self.event.set()
        # 调用join之前，先调用close函数，否则会出错。
        # 执行完close后不会有新的进程加入到pool，join函数等待所有子进程结束
        # pool.join()
        # 用于统计含有二维码图片的数量
        qr_img_num = 0
        # 用于统计操作成功的次数（包含剪切成功、删除成功、添加时间戳后剪切成功）
        op_success_num = 0
        for i in range(len(results)):
            qrcode = []
            # 每个批次执行完毕才会进来
            m = results[i].get()
            # 格式化输出结果
            for t in range(len(m)):
                img_status, op_status, qrcode_thread, note = m[t]
                name = qrcode_thread[0]
                insert_file(name)
                if img_status == 1:
                    qr_img_num += 1
                # 剪切成功、删除成功、添加时间戳后剪切成功
                if op_status in [1,3,5,8]:
                    op_success_num += 1
                    qrcode.append(qrcode_thread)
                # 显示每个批次的日志
                self.show_info(img_status, op_status, name)
                # 写入日志文件
                if self.log_file:
                    self.log_file.write(f"{note}\n")
            if self.log_file:
                self.log_file.flush()
            # 更新进度条（进度条的上限初始化为100）
            if operation == "decode":
                self.save_qrcode(cut_path, qrcode)
            else:
                if self.log_file:
                    self.save_qrcode(join(get_base_path(), "log"), qrcode, self.log_file)
            self.notifyProgress.emit((i+1)*100//num_procs)
            # logging.info(f"进程{i}结束")
        logging.info(f"扫描任务结束：")
        logging.info(f"共计检测到{qr_img_num}个包含二维码的图片，其中{op_success_num}个文件执行操作成功")
        # 清空files.db
        clean_files_table()
        # 保存操作记录
        clean_status_table()
        if self.log_file:
            self.log_file.close()
        # 使用信号槽机制，启用按钮，因为任务已经处理完成
        # 用户可以再次提交任务或创建新任务
        self.notifyStatus.emit(False)
