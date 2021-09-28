from PyQt5.QtCore import QThread, pyqtSignal
from rdsLoglib import Data, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine, Service
from datetime import timedelta
from datetime import datetime
import os
import json as js
import logging
import math
import time

def decide_old_imu(gx,gy,gz):
    for v in gx:
        if abs(round(v) - v) > 1e-5:
            return True
    for v in gy:
        if abs(round(v) - v) > 1e-5:
            return True
    for v in gz:
        if abs(round(v) - v) > 1e-5:
            return True
    return False

def rad2LSB(data):
    new_data = [v/math.pi*180.0*16.4 for v in data]
    return new_data

def Fdir2Flink(f):
    flink = " <a href='file:///" + f + "'>"+f+"</a>"
    return flink

def printData(data, fid):
    try:
        print(data, file= fid)
    except UnicodeEncodeError:
        data = data.encode(errors='ignore')  
        print(data, file= fid)
    return

class ReadThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.filenames = []
        self.log_config = "log_config.json"
        self.js = dict()
        self.content = dict()
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.service = Service()
        self.log =  []
        self.tlist = []
        self.cpu_num = 4
        self.reader = None
        self.data_keys = set()
        self.robot_keys = []
        try:
            f = open('rds_log_config.json',encoding= 'UTF-8')
            self.js = js.load(f)
        except FileNotFoundError:
            logging.error('Failed to open log_config.json')
            self.log.append('Failed to open log_config.json')

    # run method gets called when we start the thread
    def run(self):
        """读取log"""
        #初始化log数据
        try:
            f = open(self.log_config,encoding= 'UTF-8')
            self.js = js.load(f)
            f.close()
            logging.error("Load {}".format(self.log_config))
            self.log.append("Load {}".format(self.log_config))
        except FileNotFoundError:
            logging.error("Failed to open {}".format(self.log_config))
            self.log.append("Failed to open {}".format(self.log_config))
        self.content = dict()
        content_delay = dict()
        for k in self.js.keys():
            self.content[k] = Data(self.js[k])
        self.err = ErrorLine()
        self.war = WarningLine()
        self.fatal = FatalLine()
        self.notice = NoticeLine()
        self.service = Service()
        self.tlist = []
        self.log =  []
        if self.filenames:
            self.reader = ReadLog(self.filenames)
            self.reader.thread_num = self.cpu_num
            time_start=time.time()
            self.reader.parse(self.content, self.err, 
                              self.war, self.fatal, self.notice, self.service)
            time_end=time.time()
            self.log.append('read time cost: ' + str(time_end-time_start))
            # self.content.update(content_delay)
            print("123",self.content.keys())

            tmax = self.reader.tmax
            tmin = self.reader.tmin
            dt = tmax - tmin
            self.tlist = [tmin + timedelta(microseconds=x) for x in range(0, int(dt.total_seconds()*1e6+1000),1000)]
            #save Error
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_fname = "Report_" + str(ts).replace(':','-').replace(' ','_') + ".txt"
            path = os.path.dirname(self.filenames[0])
            output_fname = path + "/" + output_fname
            self.log.append("Report File:" + Fdir2Flink(output_fname))

            robot_name = set()
            self.data_keys = set()
            for k in self.content.keys():
                for robot in self.content[k].data.keys():
                    robot_name.add(robot)
                    for name in self.content[k].data[robot].keys():
                        if name != 't' and name[0] != '_':
                            self.data_keys.add(k+'.'+name)
            self.robot_keys = list(robot_name)
            self.data_keys = sorted(self.data_keys)
            fid = open(output_fname,"w") 
            print("="*20, file = fid)
            print("Files: ", self.filenames, file = fid)
            print(len(self.fatal.content()[0]), " FATALs, ", len(self.err.content()[0]), " ERRORs, ", 
                    len(self.war.content()[0]), " WARNINGs, ", len(self.notice.content()[0]), " NOTICEs", file = fid)
            self.log.append(str(len(self.fatal.content()[0])) + " FATALs, " + str(len(self.err.content()[0])) + 
                " ERRORs, " + str(len(self.war.content()[0])) + " WARNINGs, " + str(len(self.notice.content()[0])) + " NOTICEs")
            print("FATALs:", file = fid)
            for data in self.fatal.content()[0]:
                printData(data, fid)
            print("ERRORs:", file = fid)
            for data in self.err.content()[0]:
                printData(data, fid)
            print("WARNINGs:", file = fid)
            for data in self.war.content()[0]:
                printData(data, fid)
            print("NOTICEs:", file = fid)
            for data in self.notice.content()[0]:
                printData(data, fid)
            fid.close()


        self.signal.emit(self.filenames)

    def getData(self, vkey):
        if vkey in self.data:
            if not self.data[vkey][0]:
                if vkey in self.data_org_key:
                    org_key = self.data_org_key[vkey]
                    if not self.content[org_key].parsed_flag:
                        # time_start=time.time()
                        self.content[org_key].parse_now(self.reader.lines)
                        # time_end=time.time()
                        # print('real read time cost: ' + str(time_end-time_start))
                    tmp = vkey.split(".")
                    k = tmp[0]
                    name = tmp[1]
                    self.data[vkey] = (self.content[k][name], self.content[k]['t'])
            return self.data[vkey]
        else:
            return [[],[]]



