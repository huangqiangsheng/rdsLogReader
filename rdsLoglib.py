import json
import re
import math
from datetime import datetime
import codecs
import chardet
import logging
import numpy as np
import gzip
from multiprocessing import Pool, Manager
import matplotlib.pyplot as plt
def rbktimetodate(rbktime):
    """ 将rbk的时间戳转化为datatime """
    return datetime.strptime(rbktime, '%Y-%m-%d %H:%M:%S.%f')

def findrange(ts, t1, t2):
    """ 在ts中寻找大于t1小于t2对应的下标 """
    small_ind = -1
    large_ind = len(ts)-1
    for i, data in enumerate(ts):
        large_ind = i
        if(t1 <= data and small_ind < 0):
            small_ind = i
        if(t2 <= data):
            break
    return small_ind, large_ind

def polar2xy(angle, dist):
    """ 将极坐标angle,dist 转化为xy坐标 """
    x , y = [], []
    for a, d in zip(angle, dist):
        x.append(d * math.cos(a))
        y.append(d * math.sin(a))
    return x,y

class ReadLog:
    """ 读取Log """
    def __init__(self, filenames):
        """ 支持传入多个文件名称"""
        self.filenames = filenames
        self.lines = []
        self.lines_num = 0
        self.thread_num = 4
        self.sum_argv = Manager().list()
        self.argv = []
        self.tmin = None
        self.tmax = None
        self.regex = re.compile("\[(.*?)\].*")
    def _startTime(self, f, file):
        for line in f.readlines(): 
            try:
                line = line.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    line = line.decode('gbk')
                except UnicodeDecodeError:
                    logging.debug("{}: {} {}".format(file, " Skipped due to decoding failure!", line))
                    continue
            out = self.regex.match(line)
            if out:
                return rbktimetodate(out.group(1))
        return None   
    def _readData(self, f, file):
        lines = []
        for line in f.readlines(): 
            try:
                line = line.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    line = line.decode('gbk')
                except UnicodeDecodeError:
                    logging.debug("{}: {} {}".format(file, " Skipped due to decoding failure!", line))
                    continue
            lines.append(line)
        for line in lines:
            out = self.regex.match(line)
            if out:
                t = rbktimetodate(out.group(1))
                if self.tmin is None:
                    self.tmin = t
                elif self.tmin > t:
                    self.tmin = t
                break
        for line in reversed(lines):
            out = self.regex.match(line)
            if out:
                t = rbktimetodate(out.group(1))
                if self.tmax is None:
                    self.tmax = t
                elif self.tmax < t:
                    self.tmax = t
                break
        self.lines.extend(lines)

    def _do(self, lines):
        l0 = lines["l0"]
        for ind, line in enumerate(lines["data"]):
            break_flag = False
            for data in self.argv:
                if type(data).__name__ == 'dict':
                    for k in data.keys():
                        data[k].parsed_flag = True
                        if data[k].parse(line, ind + l0):
                            break_flag = True
                            break
                    if break_flag:
                        break_flag = False
                        break
                elif data.parse(line):
                    break
        self.sum_argv.append(self.argv)

    def _work(self, argv):
        self.lines_num = len(self.lines)
        al = int(self.lines_num/self.thread_num)
        if al < 1000 or self.thread_num <= 1:
            for ind, line in enumerate(self.lines):
                break_flag = False
                for data in argv:
                    if type(data).__name__ == 'dict':
                        for k in data.keys():
                            data[k].parsed_flag = True
                            if data[k].parse(line, ind):
                                break_flag = True
                                break
                        if break_flag:
                            break_flag = False
                            break
                    elif data.parse(line):
                        break     
        else:
            line_caches = []
            print("thread num:", self.thread_num, ' lines_num:', self.lines_num)
            for i in range(self.thread_num):
                if i is self.thread_num -1:
                    tmp = dict()
                    tmp['l0'] = i * al
                    tmp['data'] = self.lines[i*al:]
                    line_caches.append(tmp)
                else:
                    tmp = dict()
                    tmp['l0'] = i * al
                    tmp['data'] = self.lines[i*al:((i+1)*al)]
                    line_caches.append(tmp)
            pool = Pool(self.thread_num)
            self.argv = argv
            pool.map(self._do, line_caches)
            for s in self.sum_argv:
                for (a,b) in zip(argv,s):
                    if type(a) is dict:
                        for k in a.keys():
                            a[k].insert_data(b[k])
                    else:
                        a.insert_data(b)
            self.sum_argv = []

    def parse(self,*argv):
        """依据输入的正则进行解析"""
        file_ind = []
        file_stime = []
        for (ind,file) in enumerate(self.filenames):
            if file.endswith(".log"):
                try:
                    with open(file,'rb') as f:
                        st = self._startTime(f, file_ind)
                        if st != None:
                            file_ind.append(ind)
                            file_stime.append(st)
                except:
                    continue
            else:
                try:
                    with gzip.open(file,'rb') as f:
                        st = self._startTime(f, file_ind)
                        if st != None:
                            file_ind.append(ind)
                            file_stime.append(st) 
                except:
                    continue       
        
        max_location =sorted(enumerate(file_stime), key=lambda y:y[1])
        #print(max_location)
        
        new_file_ind = []
        for i in range(len(max_location)):
            new_file_ind.append(file_ind[max_location[i][0]])

        for i in new_file_ind:
            file = self.filenames[i]
            if file.endswith(".log"):
                try:
                    with open(file,'rb') as f:
                        self._readData(f,file)
                except:
                    continue
            else:
                try:
                    with gzip.open(file,'rb') as f:
                        self._readData(f, file)    
                except:
                    continue
        self._work(argv)


class Data:
    def __init__(self, info):
        self.type = info['type']
        self.regex = re.compile("\[(.*?)\].*\[(.*?)\]\[{}\|(.*)\]".format(self.type))
        self.short_regx = "["+self.type
        self.info = info['content']
        self.data = dict()
        self.description = dict()
        self.unit = dict()
        self.parse_error = False
        self.parsed_flag = False
        for tmp in self.info:
            if 'unit' in tmp:
                self.unit[tmp['name']] = tmp['unit']
            else:
                self.unit[tmp['name']] = ""
            if 'description' in tmp:
                self.description[tmp['name']] = tmp['description'] + " " + self.unit[tmp['name']]
            else:
                self.description[tmp['name']] = self.type + '.' + tmp['name'] + " " + self.unit[tmp['name']]

    def _storeData(self, robot, tmp, name, ind, values):
        data = self.data[robot][name]
        if tmp['type'] == 'double' or tmp['type'] == 'int64' or tmp['type'] == 'int':
            try:
                data.append(float(values[ind]))
            except:
                data.append(np.nan)
        elif tmp['type'] == 'mm':
            try:
                data.append(float(values[ind])/1000.0)
            except:
                data.append(np.nan)
        elif tmp['type'] == 'cm':
            try:
                data.append(float(values[ind])/100.0)
            except:
                data.append(np.nan)
        elif tmp['type'] == 'rad':
            try:
                data.append(float(values[ind])/math.pi * 180.0)
            except:
                data.append(np.nan)
        elif tmp['type'] == 'm':
            try:
                data.append(float(values[ind]))
            except:
                data.append(np.nan)
        elif tmp['type'] == 'LSB':
            try:
                data.append(float(values[ind])/16.03556)
            except:
                data.append(np.nan)                               
        elif tmp['type'] == 'bool':
            try:
                if values[ind] == "true" or values[ind] == "1":
                    data.append(1.0)
                else:
                    data.append(0.0)
            except:
                data.append(np.nan)
        elif tmp['type'] == 'json':
            try:
                data.append(json.loads(values[ind]))
            except:
                data.append(values[ind])
        else:
            data.apeend(values[ind])
    def parse(self, line, num):
        if self.short_regx in line:
            out = self.regex.match(line)
            if out:
                datas = out.groups()
                robot = datas[1]
                if robot not in self.data:
                    self.data[robot]=dict()
                    self.data[robot]['t'] = []
                    self.data[robot]['_lm_'] = []
                values = datas[2].split('|')
                self.data[robot]['t'].append(rbktimetodate(datas[0]))
                self.data[robot]['_lm_'].append(num)
                for tmp in self.info:
                    if 'type' in tmp and 'index' in tmp and 'name' in tmp:
                        tmp_type = type(tmp['name'])
                        name = ""
                        has_name = False
                        if tmp_type is str:
                            name = tmp['name']
                            has_name = True
                        elif tmp_type is int:
                            if tmp['name'] < len(values):
                                name = values[tmp['name']]
                                has_name = True
                        if has_name:
                            if name not in self.data[robot]:
                                self.data[robot][name] = []
                            if tmp['index'] < len(values):
                                self._storeData(robot, tmp, name, tmp['index'], values)
                            else:
                                self.data[robot][name].append(np.nan)
                    else:
                        if not self.parse_error:
                            logging.error("Error in {} {} ".format(self.type, tmp.keys()))
                            self.parse_error = True
                return True
            return False
        return False
    def parse_now(self, lines):
        if not self.parsed_flag:
            for ind, line in enumerate(lines):
                self.parse(line, ind)
                
    def __getitem__(self,k):
        return self.data[k]

    def keys(self):
        return self.data.keys()
        
    def insert_data(self, other):
        for robot in other.data.keys():
            if robot in self.data.keys():
                for key in other.data[robot].keys():
                    if key in self.data[robot].keys():
                        self.data[robot][key].extend(other.data[robot][key])
                    else:
                        self.data[robot][key] = other.data[robot][key]
            else:
                self.data[robot] = other.data[robot]


class ErrorLine:
    """  错误信息
    data[0]: t
    data[1]: 错误信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        # self.general_regex = re.compile("\[(.*?)\].*\[error\].*")
        self.regex = re.compile("\[(.*?)\].*\[error\].*\[Alarm\]\[.*?\|(.*?)\|(.*?)\|.*")
        self.short_regx = "[error"
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        if self.short_regx in line:       
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = out.group(2)
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append(out.group(3))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class WarningLine:
    """  报警信息
    data[0]: t
    data[1]: 报警信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.general_regex = re.compile("\[(.*?)\].*\[warning\].*")
        self.regex = re.compile("\[(.*?)\].*\[warning\].*\[Alarm\]\[.*?\|(.*?)\|(.*?)\|.*")
        self.short_regx = "[warning"
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        if self.short_regx in line:              
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = out.group(2)
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append(out.group(3))
                return True
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class FatalLine:
    """  错误信息
    data[0]: t
    data[1]: 报警信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[fatal\].*\[Alarm\]\[.*?\|(.*?)\|(.*?)\|.*")
        self.short_regx = "[fatal"       
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        if self.short_regx in line:                   
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = out.group(2)
                new_data_flag = True
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append(out.group(3))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class NoticeLine:
    """  注意信息
    data[0]: t
    data[1]: 注意信息内容
    data[2]: Alarm 错误编号
    data[3]: Alarm 内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Alarm\]\[Notice\|(.*?)\|(.*?)\|.*")
        self.short_regx = "[Alarm][Notice"
        self.data = [[] for _ in range(4)]
    def parse(self, line):
        if self.short_regx in line:              
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                new_num = out.group(2)
                if not new_num in self.data[2]:
                    self.data[2].append(new_num)
                    self.data[3].append(out.group(3))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def alarmnum(self):
        return self.data[2], self.data[0]
    def alarminfo(self):
        return self.data[3], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])

class Service:
    """  服务信息
    data[0]: t
    data[1]: 服务内容
    """
    def __init__(self):
        self.regex = re.compile("\[(.*?)\].*\[Service\].*")
        self.short_regx = "[Service"         
        self.data = [[] for _ in range(2)]
    def parse(self, line):
        if self.short_regx in line:               
            out = self.regex.match(line)
            if out:
                self.data[0].append(rbktimetodate(out.group(1)))
                self.data[1].append(out.group(0))
                return True
            return False
        return False
    def t(self):
        return self.data[0]
    def content(self):
        return self.data[1], self.data[0]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])


class RobotStatus:
    """  版本报错信息
    t[0]: 
    t[1]:
    data[0]: version
    data[1]: chassis
    data[2]: fatal num
    data[3]: fatal
    data[4]: error num
    data[5]: erros
    data[6]: warning num
    data[7]: warning nums
    data[8]: notice num
    data[9]: notices    
    """
    def __init__(self):
        self.regex = [re.compile("\[(.*?)\].*\[Text\]\[Robokit version: *(.*?)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Chassis Info: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[FatalNum: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Fatals: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[ErrorNum: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Errors: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[WarningNum: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Warnings: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[NoticeNum: (.*)\]"),
                    re.compile("\[(.*?)\].*\[Text\]\[Notices: (.*)\]")]
        self.short_regx = ["Robokit version:",
                           "Chassis Info:",
                           "FatalNum:",
                           "Fatals:",
                           "ErrorNum:",
                           "Errors:",
                           "WarningNum:",
                           "Warnings:",
                           "NoticeNum:",
                           "Notices"]
        self.time = [[] for _ in range(len(self.regex))]
        self.data = [[] for _ in range(len(self.regex))]
    def parse(self, line):
        for iter in range(0,10):
            if self.short_regx[iter] in line:
                out = self.regex[iter].match(line)
                if out:
                    self.time[iter].append(rbktimetodate(out.group(1)))
                    self.data[iter].append(out.group(2))
                    return True
                return False
        return False
    def t(self):
        return self.time[0]
    def version(self):
        return self.data[0], self.time[0]
    def chassis(self):
        return self.data[1], self.time[1]
    def fatalNum(self):
        return self.data[2], self.time[1]
    def fatals(self):
        return self.data[3], self.time[1]
    def errorNum(self):
        return self.data[4], self.time[1]
    def errors(self):
        return self.data[5], self.time[1]
    def warningNum(self):
        return self.data[6], self.time[1]
    def warnings(self):
        return self.data[7], self.time[1]
    def noticeNum(self):
        return self.data[8], self.time[1]
    def notices(self):
        return self.data[9], self.time[1]
    def insert_data(self, other):
        for i in range(len(self.data)):
            self.data[i].extend(other.data[i])
        for i in range(len(self.time)):
            self.time[i].extend(other.time[i])
