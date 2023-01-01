#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: 'zfb'
# time: 2022-05-03 18:02

import logging

from multiprocessing import cpu_count, Pool
from os.path import join, dirname, basename
from os import walk
from PyQt5.QtCore import QObject, pyqtSignal

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
        with open(name, "a", encoding="utf8") as f:
            for single_res in qrcode:
                if single_res is None:
                    continue
                f.write(f'"{single_res[0]}",{",".join(single_res[1])}\n')
                flag = True
            if flag:
                logging.debug(f"识别二维码结果保存到文件{name}成功！")

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
            qrcode = []
            # 每个批次执行完毕才会进来
            m = results[i].get()
            # 格式化输出结果
            for t in range(len(m)):
                name = join(final_pathes[i][t][0], final_pathes[i][t][1])
                img_status, op_status, qrcode_thread, note = m[t]
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
                    self.save_qrcode(join(dirname(__file__), "log"), qrcode, self.log_file)
            self.notifyProgress.emit((i+1)*100//num_procs)
            # logging.info(f"进程{i}结束")
        logging.info(f"扫描任务结束：")
        logging.info(f"共计检测到{qr_img_num}个包含二维码的图片，其中{op_success_num}个文件执行操作成功")
        if self.log_file:
            self.log_file.close()
        # 使用信号槽机制，启用按钮，因为任务已经处理完成
        # 用户可以再次提交任务或创建新任务
        self.notifyStatus.emit(False)
