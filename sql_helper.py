#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: 'zfb'
# time: 2023-01-04 19:03

import sqlite3

table_files_name = "files.db"
table_status_name = "status.db"

def create_files_table():
    '''
    files表用于存放未正常结束的操作，已经处理过的图片（只保存最近的一次处理结果）
    '''
    conn = sqlite3.connect(table_files_name)
    cur = conn.cursor()
    try:
        sql = """CREATE TABLE if not exists files(
                    id integer primary key autoincrement,
                    img_name varchar(1024) not null,
                    timestamp DATE DEFAULT (datetime('now','localtime'))
                );"""
        cur.execute(sql)
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        cur.close()
        conn.close()

def create_status_table(db_name="status.db"):
    '''
    status表用于上一次处理的状态
    '''
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    try:
        sql = """CREATE TABLE if not exists status(
                    id integer primary key autoincrement,
                    operation varchar(10) not null,
                    img_path varchar(1024) not null,
                    cut_path varchar(1024) default null,
                    finished integer default 0,
                    timestamp DATE DEFAULT (datetime('now','localtime'))
                );"""
        cur.execute(sql)
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        cur.close()
        conn.close()

def clean_files_table():
    conn = sqlite3.connect(table_files_name, isolation_level=None)
    cur = conn.cursor()
    try:
        sql = "DELETE FROM files;"
        cur.execute(sql)
        cur.execute("VACUUM;")
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        cur.close()
        conn.close()

def insert_file(img_name):
    '''
    存放在files表中的图片，表示已经处理过了
    '''
    conn = sqlite3.connect(table_files_name)
    cur = conn.cursor()
    try:
        sql = f"INSERT INTO files (img_name) VALUES ('{img_name}');"
        cur.execute(sql)
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        cur.close()
        conn.close()

def insert_status(operation, img_path, cut_path=None, finished=0):
    conn = sqlite3.connect(table_status_name)
    cur = conn.cursor()
    try:
        sql = f"INSERT INTO status (operation, img_path, cut_path, finished) VALUES ('{operation}', '{img_path}', '{cut_path}', {finished});"
        cur.execute(sql)
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        cur.close()
        conn.close()

def exist_file(img_name):
    conn = sqlite3.connect(table_files_name)
    cur = conn.cursor()
    try:
        sql = f"SELECT * FROM files WHERE img_name='{img_name}';"
        cur.execute(sql)
        result = cur.fetchall()
        if len(result) == 0:
            return False
        else:
            return True
    except Exception as e:
        print(e)
        return False
    finally:
        cur.close()
        conn.close()

def get_all_files():
    conn = sqlite3.connect(table_files_name)
    cur = conn.cursor()
    try:
        sql = "SELECT img_name FROM files;"
        cur.execute(sql)
        result = cur.fetchall()
        return result
    except Exception as e:
        print(e)
        return None
    finally:
        cur.close()
        conn.close()

def get_status():
    conn = sqlite3.connect(table_status_name)
    cur = conn.cursor()
    try:
        # 按id降序排列，取第一条
        sql = "SELECT operation, img_path, cut_path FROM status WHERE finished=0 ORDER BY id DESC LIMIT 1;"
        cur.execute(sql)
        result = cur.fetchall()
        if len(result) == 0:
            return None
        return result[0]
    except Exception as e:
        print(e)
        return None
    finally:
        cur.close()
        conn.close()

def clean_status_table():
    conn = sqlite3.connect(table_status_name, isolation_level=None)
    cur = conn.cursor()
    try:
        sql = "DELETE FROM status;"
        cur.execute(sql)
        cur.execute("VACUUM;")
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        cur.close()
        conn.close()