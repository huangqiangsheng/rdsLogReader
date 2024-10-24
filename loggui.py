from math import floor
import matplotlib

from SqliteView import SqliteView
matplotlib.use('Qt5Agg')
matplotlib.rcParams['font.sans-serif']=['FangSong']
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5 import QtCore, QtWidgets,QtGui
from matplotlib.figure import Figure
from datetime import datetime
from datetime import timedelta
import os, sys
from ExtendedComboBox import ExtendedComboBox
from Widget import Widget
from ReadThread import ReadThread, Fdir2Flink
from rdsLoglib import Data, ErrorLine, WarningLine, ReadLog, FatalLine, NoticeLine, Service
from MapWidget import MapWidget, Readmap
from LogViewer import LogViewer
from JsonView import DataView, JsonView
from MyToolBar import MyToolBar, RulerShapeMap
import logging
import numpy as np
import traceback
import json
from multiprocessing import freeze_support
import zipfile
from rdsLoglib import num2date, date2num

class XYSelection:
    def __init__(self, num = 1):
        self.num = num 
        self.groupBox = QtWidgets.QGroupBox('图片'+str(self.num))
        self.y_label = QtWidgets.QLabel('Data')
        self.y_combo = ExtendedComboBox()
        self.car_combo = ExtendedComboBox()
        self.car_label = QtWidgets.QLabel('AGV')
        self.service_combo = ExtendedComboBox()
        self.service = QtWidgets.QLabel('Service')
        car_form = QtWidgets.QFormLayout()
        car_form.addRow(self.car_label,self.car_combo)
        y_form = QtWidgets.QFormLayout()
        y_form.addRow(self.y_label,self.y_combo)
        service_form = QtWidgets.QFormLayout()
        service_form.addRow(self.service, self.service_combo)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(y_form)
        vbox.addLayout(car_form)
        vbox.addLayout(service_form)
        self.groupBox.setLayout(vbox)
        

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.finishReadFlag = False
        self.filenames = []
        self.lines_dict = {"fatal":[],"error":[],"warning":[],"notice":[], "service":[]} 
        self.setWindowTitle('rdsLog分析器')
        self.read_thread = ReadThread()
        self.read_thread.signal.connect(self.readFinished)
        self.mid_line_t = None #中间蓝线对应的时间
        self.mid_line_select = False #中间蓝线是否被选择上
        self.in_close = False # 是否在关闭窗口阶段
        self.map_select_lines = []
        self.mouse_pressed = False
        self.map_widget = None
        self.log_widget = None
        self.sts_widget = None
        self.dataViews = [] #显示特定数据框
        self.setupUI()

    def setupUI(self):
        """初始化窗口结构""" 
        self.setGeometry(50,50,800,900)
        self.max_fig_num = 6 
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.openLogFilesDialog,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.num_menu = QtWidgets.QMenu('&Num', self)
        self.menuBar().addMenu(self.num_menu)

        self.fig_menu = QtWidgets.QMenu('&Fig', self)
        group = QtWidgets.QActionGroup(self.fig_menu)
        texts = [str(i) for i in range(2,self.max_fig_num+1)]
        cur_id = 1
        cur_fig_num = int(texts[cur_id])
        self.robot_num = 2
        for text in texts:
            action = QtWidgets.QAction(text, self.fig_menu, checkable=True, checked=text==texts[cur_id])
            self.fig_menu.addAction(action)
            group.addAction(action)
        group.setExclusive(True)
        group.triggered.connect(self.fignum_changed)
        self.num_menu.addMenu(self.fig_menu)

        self.cpu_menu = QtWidgets.QMenu('&CPU', self)
        group = QtWidgets.QActionGroup(self.cpu_menu)
        texts = [str(i) for i in range(1, 9)]
        cur_id = 3
        cur_cpu_num = int(texts[cur_id])
        self.read_thread.cpu_num = cur_cpu_num
        for text in texts:
            action = QtWidgets.QAction(text, self.cpu_menu, checkable=True, checked=text==texts[cur_id])
            self.cpu_menu.addAction(action)
            group.addAction(action)
        group.setExclusive(True)
        group.triggered.connect(self.cpunum_changed)
        self.num_menu.addMenu(self.cpu_menu)

        self.tools_menu = QtWidgets.QMenu('&Tools', self)
        self.menuBar().addMenu(self.tools_menu)
        self.map_action = QtWidgets.QAction('&Open Map', self.tools_menu, checkable = True)
        self.map_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_M)
        self.map_action.triggered.connect(self.openMap)
        self.tools_menu.addAction(self.map_action)

        self.view_action = QtWidgets.QAction('&Open Log', self.tools_menu, checkable = True)
        self.view_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_L)
        self.view_action.triggered.connect(self.openViewer)
        self.tools_menu.addAction(self.view_action)

        self.json_action = QtWidgets.QAction('&Open Status', self.tools_menu, checkable = True)
        self.json_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_J)
        self.json_action.triggered.connect(self.openJsonView)
        self.tools_menu.addAction(self.json_action)

        self.data_action = QtWidgets.QAction('&Open Data', self.tools_menu, checkable = True)
        self.data_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_D)
        self.data_action.setChecked(True)
        self.data_action.triggered.connect(self.openDataView)
        self.tools_menu.addAction(self.data_action)
        
        self.param_action = QtWidgets.QAction('&Open Param', self.tools_menu, checkable = True)
        self.param_action.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_P)
        self.param_action.triggered.connect(self.openParamView)
        self.tools_menu.addAction(self.param_action)

        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.help_menu.addAction('&About', self.about)
        self.menuBar().addMenu(self.help_menu)

        self._main = Widget()  #主窗口
        self._main.dropped.connect(self.dragFiles)
        self.setCentralWidget(self._main)
        self.layout = QtWidgets.QVBoxLayout(self._main)
        #Add ComboBox
        self.xys = []
        self.xy_hbox = QtWidgets.QHBoxLayout()
        for i in range(0,cur_fig_num):
            selection = XYSelection(i)
            selection.car_combo.activated.connect(self.robot_combo_onActivated)
            selection.y_combo.activated.connect(self.ycombo_onActivated)
            selection.service_combo.activated.connect(self.service_combo_onActivated)
            self.xys.append(selection)
            self.xy_hbox.addWidget(selection.groupBox)
        self.layout.addLayout(self.xy_hbox)

        #消息框
        self.info = QtWidgets.QTextBrowser(self)
        self.info.setReadOnly(True)
        self.info.setMinimumHeight(5)

        #图形化结构
        self.fig_height = 2.0
        self.static_canvas = FigureCanvas(Figure(figsize=(14, self.fig_height*cur_fig_num)))
        self.static_canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.static_canvas_ORG_resizeEvent = self.static_canvas.resizeEvent
        self.static_canvas.resizeEvent = self.static_canvas_resizeEvent
        self.fig_widget = Widget()
        self.fig_layout = QtWidgets.QVBoxLayout(self.fig_widget)
        self.fig_layout.addWidget(self.static_canvas)
        self.scroll = QtWidgets.QScrollArea(self.fig_widget)
        self.scroll.setWidget(self.static_canvas)
        self.scroll.setWidgetResizable(True)
        self.scroll.keyPressEvent = self.keyPressEvent
        # self.scroll.keyReleaseEvent = self.keyReleaseEvent
        self.is_keypressed = False
        # self.layout.addWidget(self.scroll)
        self.ruler = RulerShapeMap()
        self.toolBar = MyToolBar(self.static_canvas, self._main, ruler = self.ruler)
        self.toolBar.update_home_callBack(self.new_home)
        self.addToolBar(self.toolBar)
        
        self.axs= self.static_canvas.figure.subplots(cur_fig_num, 1, sharex = True)    
        self.axs[0].tick_params(axis='x', labeltop=True, top = True)
        for ax in self.axs:
            self.ruler.add_ruler(ax)
        #鼠标移动消息
        self.static_canvas.mpl_connect('motion_notify_event', self.mouse_move)
        self.static_canvas.mpl_connect('button_press_event', self.mouse_press)
        self.static_canvas.mpl_connect('button_release_event', self.mouse_release)
        self.static_canvas.mpl_connect('pick_event', self.onpick)

        #Log
        self.log_info = QtWidgets.QTextBrowser(self)
        self.log_info.setReadOnly(True)
        self.log_info.setMinimumHeight(10)
        self.log_info.setOpenLinks(False)
        self.log_info.anchorClicked.connect(self.openFileUrl)
        # self.layout.addWidget(self.log_info)

        #消息框，绘图，Log窗口尺寸可变
        splitter1 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter1.addWidget(self.info)
        splitter1.addWidget(self.scroll)
        splitter1.setSizes([1,100])

        splitter2 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(self.log_info)
        splitter2.setSizes([100,0])
        self.layout.addWidget(splitter2)

        #选择消息框
        self.hbox = QtWidgets.QHBoxLayout()
        self.check_all = QtWidgets.QCheckBox('ALL',self)
        self.check_fatal = QtWidgets.QCheckBox('FATAL',self)
        self.check_err = QtWidgets.QCheckBox('ERROR',self)
        self.check_war = QtWidgets.QCheckBox('WARNING',self)
        self.check_notice = QtWidgets.QCheckBox('NOTICE',self)
        self.check_service = QtWidgets.QCheckBox('SERVICE',self)
        self.hbox.addWidget(self.check_all)
        self.hbox.addWidget(self.check_fatal)
        self.hbox.addWidget(self.check_err)
        self.hbox.addWidget(self.check_war)
        self.hbox.addWidget(self.check_notice)
        self.hbox.addWidget(self.check_service)
        self.hbox.setAlignment(QtCore.Qt.AlignLeft)
        self.layout.addLayout(self.hbox)
        self.check_fatal.stateChanged.connect(self.changeCheckBox)
        self.check_err.stateChanged.connect(self.changeCheckBox)
        self.check_war.stateChanged.connect(self.changeCheckBox)
        self.check_notice.stateChanged.connect(self.changeCheckBox)
        self.check_service.stateChanged.connect(self.changeCheckBox)
        self.check_all.stateChanged.connect(self.changeCheckBoxAll)
        self.check_all.setChecked(True)

        # dataView相关的初始化
        self.dataViewNewOne(None)
    
        self.map_widget = MapWidget()
        self.map_widget.setWindowIcon(QtGui.QIcon('rds.ico'))
        self.map_widget.hiddened.connect(self.mapClosed)
        self.map_widget.keyPressEvent = self.keyPressEvent

        self.param_widget = None


    def static_canvas_resizeEvent(self, event):
        self.static_canvas_ORG_resizeEvent(event)
        w = event.size().width()
        font_width = 100.0
        self.static_canvas.figure.subplots_adjust(left = (font_width/(w*1.0)), right = 0.99, bottom = 0.05, top = 0.95, hspace = 0.1)

    def get_content(self, mouse_time, ax):
        content = ""
        ind = np.where(self.axs == ax)[0][0]
        filtered_service = None
        if ind in self.read_thread.filtered_service:
            filtered_service = self.read_thread.filtered_service[ind]
        dt_min = 1e10
        if self.read_thread.fatal.t() and self.check_fatal.isChecked():
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.fatal.t()]
            if len(vdt) > 0:
                dt_min = min(vdt)
        if self.read_thread.err.t() and self.check_err.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.err.t()]
            if len(vdt) > 0:
                tmp_dt = min(vdt)
                if tmp_dt < dt_min:
                    dt_min = tmp_dt
        if self.read_thread.war.t() and self.check_war.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.war.t()]
            if len(vdt) > 0:
                tmp_dt = min(vdt)
                if tmp_dt < dt_min:
                    dt_min = tmp_dt
        if self.read_thread.notice.t() and self.check_notice.isChecked(): 
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.notice.t()]
            if len(vdt) > 0:
                tmp_dt = min(vdt)
                if tmp_dt < dt_min:
                    dt_min = tmp_dt
        if filtered_service is not None and filtered_service.t() and self.check_service.isChecked():
            vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.service.t()]
            if len(vdt) > 0:
                tmp_dt = min(vdt)
                if tmp_dt < dt_min:
                    dt_min = tmp_dt

        if dt_min < 10:
            contents = []
            if self.read_thread.fatal.t() and self.check_fatal.isChecked():
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.fatal.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.fatal.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.err.t() and self.check_err.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.err.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.err.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.war.t() and self.check_war.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.war.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.war.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if self.read_thread.notice.t() and self.check_notice.isChecked(): 
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in self.read_thread.notice.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [self.read_thread.notice.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            if filtered_service is not None and filtered_service.t() and self.check_service.isChecked():
                vdt = [abs((tmpt - mouse_time).total_seconds()) for tmpt in filtered_service.t()]
                tmp_dt = min(vdt)
                if abs(tmp_dt - dt_min) < 2e-2:
                    contents = contents + [filtered_service.content()[0][i] for i,val in enumerate(vdt) if abs(val - dt_min) < 1e-3]
            content = '\n'.join(contents)
        return content

    def updateLogView(self):
        if self.read_thread.reader and self.log_widget and self.mid_line_t is not None\
            and 'GET' in self.read_thread.content:
            min_robot = None
            min_idx = None
            min_t = None
            for robot in self.read_thread.content['GET'].data:
                if 't' in self.read_thread.content['GET'].data[robot]:
                    ts = np.array(self.read_thread.content['GET'].data[robot]['t'])
                    tmp_data = np.abs(ts - self.mid_line_t)
                    get_idx = tmp_data.argmin()
                    get_min = tmp_data[get_idx]
                    if min_robot is None:
                        min_robot = robot
                        min_idx = get_idx
                        min_t = get_min
                    else:
                        if min_t > get_min:
                            min_robot = robot
                            min_idx = get_idx
                            min_t = get_min                            
            if min_idx < 1:
                min_idx = 1

            idx = self.read_thread.content['GET'].data[min_robot]['_lm_'][min_idx]
            dt1 = (self.mid_line_t - self.read_thread.reader.tmin).total_seconds()
            dt2 = (self.read_thread.content['GET'].data[min_robot]['t'][min_idx] - self.read_thread.reader.tmin).total_seconds()
            ratio = dt1/ dt2
            idx = idx * ratio
            if idx > self.read_thread.reader.lines_num:
                idx = self.read_thread.reader.lines_num
            if idx < 0:
                idx = 0
            self.log_widget.setLineNum(floor(idx))

    def updateJsonView(self):
        if self.sts_widget:
            if len(self.read_thread.rstatus.chassis()[1]) <1:
                return
            ts = np.array(self.read_thread.rstatus.chassis()[1])
            idx = (np.abs(ts - self.mid_line_t)).argmin()
            j = json.loads(self.read_thread.rstatus.chassis()[0][idx])   
            if idx < len(self.read_thread.rstatus.version()[0]):
                j["VERSION"] = "{}.{}".format(self.read_thread.rstatus.version()[0][idx],
                                                                    j["PRODUCT_FULL_VERSION"])
            if idx < len(self.read_thread.rstatus.fatalNum()[0]):
                j["fatalNums"] = self.read_thread.rstatus.fatalNum()[0][idx]
            if idx < len(self.read_thread.rstatus.fatals()[0]):
                try:
                    j["fatals"] = json.loads(self.read_thread.rstatus.fatals()[0][idx])
                except:
                    j["fatals"] = self.read_thread.rstatus.fatals()[0][idx]
            if idx < len(self.read_thread.rstatus.errorNum()[0]):
                j["errorNums"] = self.read_thread.rstatus.errorNum()[0][idx]
            if idx < len(self.read_thread.rstatus.errors()[0]):
                try:
                    j["errors"] = json.loads(self.read_thread.rstatus.errors()[0][idx])
                except:
                    j["errors"] = self.read_thread.rstatus.errors()[0][idx]
            if idx < len(self.read_thread.rstatus.warningNum()[0]):
                j["warningNum"] = self.read_thread.rstatus.warningNum()[0][idx]
            if idx < len(self.read_thread.rstatus.warnings()[0]):
                try:
                    j["warnings"] = json.loads(self.read_thread.rstatus.warnings()[0][idx])
                except:
                    j["warnings"] = self.read_thread.rstatus.warnings()[0][idx]
            if idx < len(self.read_thread.rstatus.noticeNum()[0]):
                j["noticeNum"] = self.read_thread.rstatus.noticeNum()[0][idx]
            if idx < len(self.read_thread.rstatus.notices()[0]):
                try:
                    j["notices"] = json.loads(self.read_thread.rstatus.notices()[0][idx])
                except:
                    j["notices"] = self.read_thread.rstatus.notices()[0][idx]
            self.sts_widget.loadJson(j)

    def getValidYItems(self,robot):
        yitems = []
        for y in self.read_thread.content:
            if robot in self.read_thread.content[y].data:
                value = self.read_thread.content[y].data[robot]
                t = self.read_thread.content[y].data[robot]['t']    
                if value is not None and t is not None:
                    yitems.append(y)
        if robot == "global":
            yitems.append("memory")
        return yitems

    def updateDataView(self, d:DataView):
        robot = d.selection.car_combo.currentText()
        first_k = d.selection.y_combo.currentText()
        value = None
        t = None
        if first_k in self.read_thread.content \
            and robot in self.read_thread.content[first_k].data:
            value = self.read_thread.content[first_k].data[robot]
            t = self.read_thread.content[first_k].data[robot]['t']
        elif robot == "global" and first_k == "memory":
            value, t = self.read_thread.memory.content["rbk_phy"]()
        if value is None or t is None:
            yitems = self.getValidYItems(robot)
            d.setYItems(yitems)
            return
        if len(t) <1:
            return
        ts = np.array(t)
        idx = (np.abs(ts - self.mid_line_t)).argmin()
        if ts[idx] > self.mid_line_t and idx > 0:
            idx -= 1
        j = dict()
        if robot == "global" and first_k == "memory":
            for k in self.read_thread.memory.content:
                tmp_d = self.read_thread.memory.content[k]()[0]
                if idx < len(tmp_d):
                    j[k] = tmp_d[idx]
                else:
                    j[k] = None
        else:
            for k in self.read_thread.content[first_k].data[robot].keys():
                if k[0] == '_':
                    continue
                j[k] = self.read_thread.content[first_k].data[robot][k][idx]
                # 对于订单特殊处理
                if isinstance(j[k], dict):
                    if "createTime" in j[k]:
                        if isinstance(j[k]["createTime"], int):
                            j[k]["createTime"] = datetime.fromtimestamp(j[k]["createTime"])
                    if "terminalTime" in j[k]:
                        if isinstance(j[k]["terminalTime"], int):
                            j[k]["terminalTime"] = datetime.fromtimestamp(j[k]["terminalTime"])
        d.loadJson(j)

    def updateDataViews(self):
        for d in self.dataViews:
            self.updateDataView(d)
    def updateParam(self):
        if not self.filenames:
            return
        dir_name, _ = os.path.split(self.filenames[0])
        pdir_name, _ = os.path.split(dir_name)
        param_dir = os.path.join(pdir_name,"params")
        param_file_name = os.path.join(param_dir, "robot.param")
        self.param_widget.fileOpenStartup(param_file_name)
    def updateMap(self):
        if self.mid_line_t is None:
            return
        self.updateMapSelectLine()
        self.updateLogView()
        self.updateJsonView()
        self.updateDataViews()

        if self.filenames:
            full_map_name = None
            dir_name, _ = os.path.split(self.filenames[0])
            pdir_name, _ = os.path.split(dir_name)
            map_dir = os.path.join(pdir_name,"scene")
            if os.path.isdir(map_dir):
                full_map_name = os.path.join(map_dir,"scene")
                if not os.path.isdir(full_map_name):
                    zip_name = os.path.join(map_dir, "scene.zip")
                    print("extract ", zip_name)
                    fz = zipfile.ZipFile(zip_name, 'r')
                    for file in fz.namelist():
                        fz.extract(file, full_map_name)      
                else:
                    print("use org scene file")
                full_map_name = os.path.join(full_map_name,"rds.scene")
                self.map_widget.readFiles([full_map_name])   

        for robot in self.read_thread.content['rTopoPos'].data:
            loc_idx = -1
            loc_ts = np.array(self.read_thread.content['rTopoPos'].data[robot]['t'])
            loc_idx = (np.abs(loc_ts - self.mid_line_t)).argmin()
            if loc_ts[loc_idx] > self.mid_line_t and loc_idx > 0:
                    loc_idx -= 1
            area_idx = -1
            get_ts = np.array(self.read_thread.content['GET'].data[robot]['t'])
            area_idx = (np.abs(get_ts - self.mid_line_t)).argmin()
            if get_ts[area_idx] > self.mid_line_t and area_idx > 0:
                area_idx -= 1
            max_idx = 100
            parea_idx = area_idx
            cur_area_name = self.read_thread.content['GET'].data[robot]['cu_area_name'][area_idx]
            for idx in range(area_idx):
                if area_idx - idx - 1 < 0:
                    parea_idx = 0
                if self.read_thread.content['GET'].data[robot]['cu_area_name'][area_idx - idx - 1] != cur_area_name:
                    parea_idx = area_idx - idx
                    break
                if idx > max_idx:
                    parea_idx = area_idx - idx - 1
                    break        
            pt = get_ts[parea_idx]
            path_ts = np.array(self.read_thread.content['OccupyRes'].data[robot]['t'])
            path_idx = (np.abs(path_ts - self.mid_line_t)).argmin()
            if path_ts[path_idx] > self.mid_line_t and path_idx > 0:
                    path_idx -= 1
            self.map_widget.readtrajectory(robot,
                self.read_thread.content['GET'].data[robot]['cu_area_name'][area_idx],
                self.read_thread.content['OccupyRes'].data[robot]['path'][path_idx],
                self.read_thread.content['rTopoPos'].data[robot]['x'][loc_idx], 
                self.read_thread.content['rTopoPos'].data[robot]['y'][loc_idx], 
                np.deg2rad(self.read_thread.content['rTopoPos'].data[robot]['theta'][loc_idx]),
                self.mid_line_t)           
        self.map_widget.redraw()

    def mouse_press(self, event):
        self.mouse_pressed = True
        if event.inaxes and self.finishReadFlag:
            mouse_time = num2date(event.xdata) 
            if event.button == 1:
                content = event.inaxes.get_ylabel().replace(' \n ', ".") + ' : ' + str(mouse_time) + ',\t' +str(event.ydata)
                self.log_info.append(content)
            elif event.button == 3:
                if not self.toolBar.isActive():
                    self.popMenu = QtWidgets.QMenu(self)
                    self.popMenu.addAction('&Save Data',lambda:self.savePlotData(event.inaxes))
                    self.popMenu.addAction('&Move Here',lambda:self.moveHere(event.xdata))
                    self.popMenu.addAction('&Diff Time', lambda:self.diffData(event.inaxes))
                    self.popMenu.addAction('&-y', lambda:self.negData(event.inaxes))
                    cursor = QtGui.QCursor()
                    self.popMenu.exec_(cursor.pos())
                # show info
                content = self.get_content(mouse_time, event.inaxes)
                if content != "":
                    self.log_info.append(content[:-1])
            if self.mid_line_select:
                self.mid_line_t = mouse_time
                self.updateMap()

    def mouse_move(self, event):
        if event.inaxes and self.finishReadFlag:
            mouse_time = num2date(event.xdata)
            content = self.get_content(mouse_time, event.inaxes)
            self.info.setText(content)
            if self.mid_line_select:
                self.mid_line_t = mouse_time
                self.updateMap()
        elif not self.finishReadFlag:
            self.info.setText("")

    def mouse_release(self, event):
        self.mouse_pressed = False
        self.mid_line_select = False

    def moveHere(self, mtime):
        mouse_time = mtime
        if type(mouse_time) is not datetime:
            mouse_time = num2date(mouse_time)
        self.mid_line_t = mouse_time
        self.updateMap()

    def savePlotData(self, cur_ax):
        pass
        # indx = self.axs.tolist().index(cur_ax)
        # xy = self.xys[indx]
        # group_name = xy.y_combo.currentText().split('.')[0]
        # outdata = []
        # if xy.x_combo.currentText() == 't':
        #     tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        #     list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        #     list_tmpdata.sort(key=lambda d: d[0])
        #     for data in list_tmpdata:
        #         outdata.append("{},{}".format(data[0].strftime('%Y-%m-%d %H:%M:%S.%f'), data[1]))
        # elif xy.x_combo.currentText() == 'timestamp':
        #     org_t = self.read_thread.getData(group_name + '.timestamp')[0]
        #     dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
        #     t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
        #     tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], t)
        #     list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        #     list_tmpdata.sort(key=lambda d: d[0])
        #     for data in list_tmpdata:
        #         outdata.append("{},{}".format(data[0], data[1]))
        # fname, _ = QtWidgets.QFileDialog.getSaveFileName(self,"选取log文件", "","CSV Files (*.csv);;All Files (*)")
        # logging.debug('Save ' + xy.y_combo.currentText() + ' and ' + xy.x_combo.currentText() + ' in ' + fname)
        # if fname:
        #     try:
        #         with open(fname, 'w') as fn:
        #             for d in outdata:
        #                 fn.write(d+'\n')
        #     except:
        #         pass

    def diffData(self, cur_ax):
        pass
        # indx = self.axs.tolist().index(cur_ax)
        # xy = self.xys[indx]        
        # group_name = xy.y_combo.currentText().split('.')[0]
        # list_tmpdata = []
        # org_t = self.read_thread.getData(group_name + '.timestamp')[0]
        # if len(org_t) > 0:
        #     dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
        #     t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
        #     tmpdata = (self.read_thread.getData(xy.y_combo.currentText())[0], t)
        #     list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        # else:
        #     tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        #     list_tmpdata = [(t,d) for t,d in zip(tmpdata[1], tmpdata[0])]
        # if len(list_tmpdata) < 2:
        #     return
        # list_tmpdata.sort(key=lambda d: d[0])
        # dts = [(a[0]-b[0]).total_seconds() for a, b in zip(list_tmpdata[1::], list_tmpdata[0:-1])]
        # dvs = [a[1]-b[1] for a, b in zip(list_tmpdata[1::], list_tmpdata[0:-1])]
        # try:
        #     dv_dt = [a/b if abs(b) > 1e-12 else np.nan for a, b in zip(dvs, dts)]
        #     self.drawdata(cur_ax, (dv_dt, list_tmpdata[1::]), 'diff_'+group_name, False)
        # except ZeroDivisionError:
        #     pass

    def negData(self, cur_ax):
        pass
        # indx = self.axs.tolist().index(cur_ax)
        # xy = self.xys[indx]        
        # group_name = xy.y_combo.currentText().split('.')[0]
        # org_t = self.read_thread.getData(group_name + '.timestamp')[0]
        # if len(org_t) > 0:
        #     dt = [timedelta(seconds = (tmp_t/1e9 - org_t[0]/1e9)) for tmp_t in org_t]
        #     t = [self.read_thread.getData(xy.y_combo.currentText())[1][0] + tmp for tmp in dt]
        #     tmpdata = [self.read_thread.getData(xy.y_combo.currentText())[0], t]
        #     tmpdata[0] = [-a for a in tmpdata[0]]
        #     self.drawdata(cur_ax, (tmpdata[0], tmpdata[1]), group_name, False)
        # else:
        #     tmpdata = self.read_thread.getData(xy.y_combo.currentText())
        #     data = [-a for a in tmpdata[0]]
        #     self.drawdata(cur_ax, (data, tmpdata[1]), '-'+xy.y_combo.currentText(), False)

    def onpick(self, event):
        if self.map_action.isChecked() \
        or self.view_action.isChecked() \
        or self.json_action.isChecked() \
        or self.data_action.isChecked():
            self.mid_line_select = True
        else:
            self.mid_line_select = False

    def keyPressEvent(self,event):
        pass
        # if self.map_action.isChecked():
        #     if len(self.map_select_lines) > 1:
        #         if (event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D
        #             or event.key() == QtCore.Qt.Key_Left or event.key() == QtCore.Qt.Key_Right):
        #             cur_t = self.map_select_lines[0].get_xdata()[0]
        #             if type(cur_t) is not datetime:
        #                 cur_t = cur_t * 86400 - 62135712000
        #                 cur_t = datetime.fromtimestamp(cur_t)
        #             if event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D:
        #                 self.key_laser_idx = -1
        #                 self.key_laser_channel = -1
        #                 t = np.array(self.read_thread.content['LocationEachFrame']['t'])
        #                 if self.key_loc_idx < 0:
        #                     self.key_loc_idx = (np.abs(t-cur_t)).argmin()
        #                 if event.key() == QtCore.Qt.Key_A:
        #                     if self.key_loc_idx > 0:
        #                         self.key_loc_idx = self.key_loc_idx - 1
        #                 if event.key() ==  QtCore.Qt.Key_D:
        #                     if self.key_loc_idx < (len(t) -1 ):
        #                         self.key_loc_idx = self.key_loc_idx + 1
        #                 cur_t = t[self.key_loc_idx]
        #             else:
        #                 self.key_loc_idx = -1
        #                 if self.key_laser_idx < 0:
        #                     min_laser_channel = -1
        #                     laser_idx = -1
        #                     min_dt = None
        #                     for index in self.read_thread.laser.datas.keys():
        #                         t = np.array(self.read_thread.laser.t(index))
        #                         if len(t) < 1:
        #                             continue
        #                         tmp_laser_idx = (np.abs(t-cur_t)).argmin()
        #                         tmp_dt = np.min(np.abs(t-cur_t))
        #                         if min_dt == None or tmp_dt < min_dt:
        #                             min_laser_channel = index
        #                             laser_idx = tmp_laser_idx
        #                             min_dt = tmp_dt
        #                     self.key_laser_idx = laser_idx
        #                     self.key_laser_channel = min_laser_channel
        #                     t = self.read_thread.laser.t(min_laser_channel)
        #                     cur_t = t[laser_idx]
        #                 if event.key() == QtCore.Qt.Key_Left:
        #                     self.key_laser_idx = self.key_laser_idx -1
        #                     t = self.read_thread.laser.t(self.key_laser_channel)
        #                     if self.key_laser_idx < 0:
        #                         self.key_laser_idx = len(t) - 1
        #                     cur_t = t[self.key_laser_idx]
        #                 if event.key() == QtCore.Qt.Key_Right:
        #                     self.key_laser_idx = self.key_laser_idx + 1
        #                     t = self.read_thread.laser.t(self.key_laser_channel)
        #                     if self.key_laser_idx >= len(t):
        #                         self.key_laser_idx = 0
        #                     cur_t = t[self.key_laser_idx]
        #             self.updateMap(cur_t, self.key_loc_idx, self.key_laser_idx, self.key_laser_channel)


    # def keyReleaseEvent(self, event): #####
    #     print("keyRelease {}".format(event.key()))
    #     if event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_D:
    #         self.key_loc_idx = -1
    #     if event.key() == QtCore.Qt.Key_Left or event.key() == QtCore.Qt.Key_Right:
    #         self.key_laser_idx = -1
    #         self.key_laser_channel = -1

    def new_home(self, *args, **kwargs):
        for ax, xy in zip(self.axs, self.xys):
            robot = xy.car_combo.currentText()
            text = xy.y_combo.currentText()
            tmp = text.split('.')
            if len(tmp)  == 2:
                first_k = tmp[0]
                sec_k = tmp[1] 
                if first_k in self.read_thread.content \
                    and robot in self.read_thread.content[first_k].data\
                        and sec_k in self.read_thread.content[first_k].data[robot]:
                    data = self.read_thread.content[first_k].data[robot][sec_k]
                    if len(data)> 0 and (isinstance(data[0], float) or isinstance(data[0], int)) :
                        tmpd = np.array(data)
                        tmpd = tmpd[~np.isnan(tmpd)]
                        if len(tmpd) > 0:
                            max_range = max(max(tmpd) - min(tmpd), 1e-6)
                            ax.set_ylim(min(tmpd) - 0.05 * max_range, max(tmpd)  + 0.05 * max_range)
                            ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
        self.static_canvas.figure.canvas.draw()

    def new_forward(self, *args, **kwargs):
        xmin,xmax =  self.axs[0].get_xlim()
        range = xmax - xmin
        xmin = xmin + range /10.0
        xmax = xmax + range /10.0
        for ax in self.axs:
            ax.set_xlim(xmin,xmax)
        self.static_canvas.figure.canvas.draw()

    def new_back(self, *args, **kwargs):
        xmin,xmax =  self.axs[0].get_xlim()
        range = xmax - xmin
        xmin = xmin - range /10.0
        xmax = xmax - range /10.0
        for ax in self.axs:
            ax.set_xlim(xmin,xmax)
        self.static_canvas.figure.canvas.draw()

    def openFileUrl(self, flink):
        QtGui.QDesktopServices.openUrl(flink)

    def openLogFilesDialog(self):
        # self.setGeometry(50,50,640,480)
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        self.filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,"选取log文件", "","Log Files (*.log);;All Files (*)", options=options)
        if self.filenames:
            self.finishReadFlag = False
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            logging.debug('Loading ' + str(len(self.filenames)) + ' Files:')
            self.log_info.append('Loading '+str(len(self.filenames)) + ' Files:')
            for (ind, f) in enumerate(self.filenames):
                logging.debug(str(ind+1)+':'+f)
                flink = Fdir2Flink(f)
                self.log_info.append(str(ind+1)+':'+flink)
            self.setWindowTitle('Loading')

    def dragFiles(self, files):
        flag_first_in = True
        for file in files:
            if os.path.exists(file):
                subffix = os.path.splitext(file)[1]
                if subffix == ".log" or subffix == ".gz":
                    if flag_first_in:
                        self.filenames = []
                        flag_first_in = False
                    self.filenames.append(file)
                elif os.path.splitext(file)[1] == ".json":
                    logging.debug('Update log_config.json')
                    self.read_thread.log_config = file
                else: 
                    logging.debug('fail to load {}'.format(file))
                    return
        if self.filenames:
            self.finishReadFlag = False
            self.read_thread.filenames = self.filenames
            self.read_thread.start()
            logging.debug('Loading' + str(len(self.filenames)) + 'Files:')
            self.log_info.append('Loading '+str(len(self.filenames)) + ' Files:')
            for (ind, f) in enumerate(self.filenames):
                logging.debug(str(ind+1) + ':' + f)
                flink = Fdir2Flink(f)
                self.log_info.append(str(ind+1)+':'+flink)
            self.setWindowTitle('Loading')

    def readFinished(self, result):
        for tmps in self.read_thread.log:
            self.log_info.append(tmps)
        logging.debug('read Finished')
        self.log_info.append('Finished')
        max_line = 1000
        if len(self.read_thread.fatal.t()) > max_line:
            logging.warning("FATALs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.fatal.t())))
            self.log_info.append("FATALs are too much to be ploted. Max Number is "+ str(max_line) + ". Current Number is " + str(len(self.read_thread.fatal.t())))
            self.read_thread.fatal = FatalLine()
        if len(self.read_thread.err.t()) > max_line:
            logging.warning("ERRORs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.err.t())))
            self.log_info.append("ERRORs are too much to be ploted. Max Number is " + str(max_line)+". Current Number is "+str(len(self.read_thread.err.t())))
            self.read_thread.err = ErrorLine()
        if len(self.read_thread.war.t()) > max_line:
            logging.warning("WARNINGs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.war.t())))
            self.log_info.append("WARNINGs are too much to be ploted. Max Number is " + str(max_line) +  ". Current Number is " + str(len(self.read_thread.war.t())))
            self.read_thread.war = WarningLine()
        if len(self.read_thread.notice.t()) > max_line:
            logging.warning("NOTICEs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.notice.t())))
            self.log_info.append("NOTICEs are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.notice.t())))
            self.read_thread.notice = NoticeLine()
        # if len(self.read_thread.service.t()) > max_line:
        #     logging.warning("SERVICE are too much to be ploted. Max Number is " + str(max_line) +". Current Number is " + str(len(self.read_thread.service.t())))
        #     self.log_info.append("SERVICE are too much to be ploted. Max Number is " + str(max_line) + ". Current Number is " + str(len(self.read_thread.service.t())))
        #     self.read_thread.service = Service()
        self.finishReadFlag = True
        self.setWindowTitle('Log分析器: {0}'.format([f.split('/')[-1] for f in self.filenames]))
        if self.read_thread.filenames:
            #画图 mcl.t, mcl.x
            self.map_select_lines = []
            for i, xys in enumerate(self.xys):
                last_combo_ind = xys.car_combo.currentIndex()
                xys.car_combo.clear()
                xys.car_combo.addItems(self.read_thread.robot_keys)
                if last_combo_ind >= 0:
                        xys.car_combo.setCurrentIndex(last_combo_ind)
                last_combo_ind = xys.y_combo.currentIndex()
                xys.y_combo.clear()
                car_name = xys.car_combo.currentText()
                if car_name in self.read_thread.data_keys:
                    xys.y_combo.addItems(self.read_thread.data_keys[car_name])
                if last_combo_ind >= 0:
                    xys.y_combo.setCurrentIndex(last_combo_ind)

                last_combo_ind = xys.service_combo.currentIndex()
                xys.service_combo.clear()
                xys.service_combo.addItems(self.read_thread.service_keys)
                if last_combo_ind >= 0:
                    xys.service_combo.setCurrentIndex(last_combo_ind)
            for d in self.dataViews:
                self.initDataView(d)

            for i, ax in enumerate(self.axs):
                    self.drawdata(ax, self.xys[i].car_combo.currentText(), 
                        self.xys[i].y_combo.currentText(),
                        self.xys[i].service_combo.currentText(),
                        True)
            self.updateMidLine()
            self.updateMapSelectLine()
            self.openMap(self.map_action.isChecked())
            self.openViewer(self.view_action.isChecked())
            self.openJsonView(self.json_action.isChecked())
            self.openDataView(self.data_action.isChecked())
            self.openParamView(self.param_action.isChecked())
            self.updateMap()


    def fileQuit(self):
        self.close()

    def about(self):
        QtWidgets.QMessageBox.about(self, "关于", """Log Viewer V2.3.1a""")

    def ycombo_onActivated(self):
        curcombo = self.sender()
        index = 0
        for (i, xys) in enumerate(self.xys):
            index = i
            if xys.y_combo == curcombo:
                break; 
            
        ax = self.axs[index]

        logging.info("Fig {} {} {}".format(index, self.xys[index].car_combo.currentText(), self.xys[index].y_combo.currentText()))
        self.drawdata(ax, self.xys[index].car_combo.currentText(), self.xys[index].y_combo.currentText(), self.xys[index].service_combo.currentText(), False)
    
    def robot_combo_onActivated(self):
        curcombo = self.sender()
        index = 0
        for (i, xys) in enumerate(self.xys):
            if curcombo == xys.car_combo:
                index = i
                break
        
        text = curcombo.currentText()
        cur_y = self.xys[index].y_combo.currentText()
        self.xys[index].y_combo.clear()
        if text in self.read_thread.data_keys:
            self.xys[index].y_combo.addItems(self.read_thread.data_keys[text])
            if cur_y in self.read_thread.data_keys[text]:
                indx = list(self.read_thread.data_keys[text]).index(cur_y)
                self.xys[index].y_combo.setCurrentIndex(indx)
        print("Fig", text, index, self.xys[index].car_combo.currentText(), self.xys[index].y_combo.currentText())
        self.drawdata(self.axs[index], self.xys[index].car_combo.currentText(), self.xys[index].y_combo.currentText(), self.xys[index].service_combo.currentText(), False)

    def service_combo_onActivated(self):
        curcombo = self.sender()
        index = 0
        for (i, xys) in enumerate(self.xys):
            if curcombo == xys.service_combo:
                index = i
                break
        text = curcombo.currentText()

        print("Fig", text, index, self.xys[index].car_combo.currentText(), self.xys[index].y_combo.currentText(), self.xys[index].service_combo.currentText())
        self.drawdata(self.axs[index], self.xys[index].car_combo.currentText(), self.xys[index].y_combo.currentText(), self.xys[index].service_combo.currentText(), False)

    def cpunum_changed(self, action):
        self.read_thread.cpu_num = int(action.text())

    def fignum_changed(self,action):
        new_fig_num = int(action.text())
        logging.info('fignum_changed to '+str(new_fig_num))
        last_xrange = []
        for ax_ind in range(len(self.axs)):
            xmin, xmax = self.axs[ax_ind].get_xlim()
            last_xrange.append([xmin, xmax])
        for ax in self.axs:
            self.static_canvas.figure.delaxes(ax)

        self.static_canvas.figure.set_figheight(new_fig_num*self.fig_height)
        self.axs= self.static_canvas.figure.subplots(new_fig_num, 1, sharex = True)
        self.axs[0].tick_params(axis='x', labeltop=True, top = True)

        self.ruler.clear_rulers()
        for ax in self.axs:
            self.ruler.add_ruler(ax)
        self.static_canvas.figure.canvas.draw()
        self.scroll.setWidgetResizable(True)
        for i in range(0, self.xy_hbox.count()): 
            self.xy_hbox.itemAt(i).widget().deleteLater()

        combo_ind = [] 
        for xy in self.xys:
            robot_ind = xy.car_combo.currentIndex()
            y_ind = xy.y_combo.currentIndex()
            service_ind = xy.service_combo.currentIndex()
            combo_ind.append((robot_ind, y_ind, service_ind))

        self.xys = []
        for i in range(0, new_fig_num):
            selection = XYSelection(i)
            selection.car_combo.activated.connect(self.robot_combo_onActivated)
            selection.y_combo.activated.connect(self.ycombo_onActivated)
            selection.service_combo.activated.connect(self.service_combo_onActivated)
            self.xys.append(selection)
            self.xy_hbox.addWidget(selection.groupBox)

        if self.finishReadFlag and self.read_thread.filenames:
            self.map_select_lines = []
            for i, xys in enumerate(self.xys):
                xys.car_combo.addItems(self.read_thread.robot_keys)
                if i < len(combo_ind):
                    xys.car_combo.setCurrentIndex(combo_ind[i][0])
                combo = xys.y_combo
                print("change Figure")
                car_name = xys.car_combo.currentText()
                if car_name in self.read_thread.data_keys:
                    combo.addItems(self.read_thread.data_keys[car_name])
                if i < len(combo_ind):
                    xys.y_combo.setCurrentIndex(combo_ind[i][1])
                xys.service_combo.addItems(self.read_thread.service_keys)
                if i< len(combo_ind):
                    xys.car_combo.setCurrentIndex(combo_ind[i][2])

            for i, ax in enumerate(self.axs):
                ax.set_xlim(last_xrange[i][0], last_xrange[i][1])
                self.drawdata(ax, self.xys[i].car_combo.currentText(),
                              self.xys[i].y_combo.currentText(),
                              self.xys[i].service_combo.currentText(),
                              True)

            # self.updateMapSelectLine()


    def drawdata(self, ax, robot, data, service, resize = False):
        xmin,xmax =  ax.get_xlim()
        ax.cla()
        self.drawFEWN(ax,service)
        tmp = data.split('.')
        if len(tmp)  == 2:
            first_k = tmp[0]
            sec_k = tmp[1]
            value = None
            t = None
            ylabel = ""
            if first_k == "memory":
                if sec_k in self.read_thread.memory.content:
                    value, t = self.read_thread.memory.content[sec_k]()
                ylabel = data
            else:
                if robot in self.read_thread.content[first_k].data:
                    value = self.read_thread.content[first_k].data[robot][sec_k]
                    t = self.read_thread.content[first_k].data[robot]['t']
                    ylabel = "{} \n {}".format(robot, self.read_thread.content[first_k].description[sec_k])
            if value and t:
                ax.plot(t, value, '.')
                if len(value) > 0 and isinstance(value[0], (int, float)):
                    tmpd = np.array(value)
                    tmpd = tmpd[~np.isnan(tmpd)]
                    if len(tmpd) > 0:
                        max_range = max(max(tmpd) - min(tmpd), 1.0)
                        ax.set_ylim(min(tmpd) - 0.05 * max_range, max(tmpd) + 0.05 * max_range)
            if resize:
                ax.set_xlim(self.read_thread.tlist[0], self.read_thread.tlist[-1])
            else:
                ax.set_xlim(xmin, xmax)
            ax.set_ylabel(ylabel)
            ax.grid()
            ind = np.where(self.axs == ax)[0][0]
            if self.map_select_lines:
                ax.add_line(self.map_select_lines[ind])
            self.ruler.add_ruler(ax)
            self.static_canvas.figure.canvas.draw()

    def drawFEWN(self,ax, service=""):
        """ 绘制 Fatal, Error, Warning在坐标轴上"""
        fl, el, wl,nl = None, None, None, None
        self.lines_dict = dict()
        line_num = 0
        legend_info = []
        fnum, ernum, wnum, nnum = [], [], [], [] 
        tsenum = []
        tse = None
        lw = 1.5
        ap = 0.8
        # filter service
        filtered_service = None
        if not service == "":
            filtered_service = self.read_thread.service
            service_selected = Service()
            data_len = len(filtered_service.data[0])
            for i in range(0, data_len):
                if filtered_service.data[2][i] == service:
                    service_selected.data[0].append(filtered_service.data[0][i])
                    service_selected.data[1].append(filtered_service.data[1][i])
                    service_selected.data[2].append(filtered_service.data[2][i])
            filtered_service = service_selected
            ind = np.where(self.axs == ax)[0][0]
            self.read_thread.filtered_service[ind] = filtered_service
        if filtered_service is not None:
            for tmp in filtered_service.t():
                tse = ax.axvline(tmp, linestyle = '-', color = 'k', linewidth = lw, alpha = ap)
                tsenum.append(line_num)
                line_num = line_num + 1
        if tse:
            legend_info.append(tse)
            legend_info.append('service')
        for tmp in self.read_thread.fatal.t():
            fl= ax.axvline(tmp, linestyle='-',color = 'm', linewidth = lw, alpha = ap)
            fnum.append(line_num)
            line_num = line_num + 1
        if fl:
            legend_info.append(fl)
            legend_info.append('fatal')
        for tmp in self.read_thread.err.t():
            el= ax.axvline(tmp, linestyle = '-.', color='r', linewidth = lw, alpha = ap)
            ernum.append(line_num)
            line_num = line_num + 1
        if el:
            legend_info.append(el)
            legend_info.append('error')
        for tmp in self.read_thread.war.t():
            wl = ax.axvline(tmp, linestyle = '--', color = 'y', linewidth = lw, alpha = ap)
            wnum.append(line_num)
            line_num = line_num + 1
        if wl:
            legend_info.append(wl)
            legend_info.append('warning')
        for tmp in self.read_thread.notice.t():
            nl = ax.axvline(tmp, linestyle = ':', color = 'g', linewidth = lw, alpha = ap)
            nnum.append(line_num)
            line_num = line_num + 1
        if nl:
            legend_info.append(nl)
            legend_info.append('notice')
        if legend_info:
            ax.legend(legend_info[0::2], legend_info[1::2], loc='upper right')
        self.lines_dict['fatal'] = fnum
        self.lines_dict['error'] = ernum
        self.lines_dict['warning'] = wnum
        self.lines_dict['notice'] = nnum
        self.lines_dict['service'] = tsenum
        lines = ax.get_lines()
        for n in fnum:
            lines[n].set_visible(self.check_fatal.isChecked())
        for n in ernum:
            lines[n].set_visible(self.check_err.isChecked())
        for n in wnum:
            lines[n].set_visible(self.check_war.isChecked())
        for n in nnum:
            lines[n].set_visible(self.check_notice.isChecked())
        for n in tsenum:
            lines[n].set_visible(self.check_service.isChecked())
        
    def updateCheckInfoLine(self,key):
        for ax in self.axs:
            lines = ax.get_lines()
            for num in self.lines_dict[key]:
                vis = not lines[num].get_visible()
                lines[num].set_visible(vis)
        self.static_canvas.figure.canvas.draw()


    def changeCheckBox(self):
        if self.check_err.isChecked() and self.check_fatal.isChecked() and self.check_notice.isChecked() and \
        self.check_war.isChecked() and \
        self.check_service.isChecked():
            self.check_all.setCheckState(QtCore.Qt.Checked)
        elif self.check_err.isChecked() or self.check_fatal.isChecked() or self.check_notice.isChecked() or \
        self.check_war.isChecked() or \
        self.check_service.isChecked():
            self.check_all.setTristate()
            self.check_all.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            self.check_all.setTristate(False)
            self.check_all.setCheckState(QtCore.Qt.Unchecked)

        cur_check = self.sender()
        if cur_check is self.check_fatal:
            self.updateCheckInfoLine('fatal')
        elif cur_check is self.check_err:
            self.updateCheckInfoLine('error')
        elif cur_check is self.check_war:
            self.updateCheckInfoLine('warning')
        elif cur_check is self.check_notice:
            self.updateCheckInfoLine('notice')
        elif cur_check is self.check_service:
            self.updateCheckInfoLine('service')

    def changeCheckBoxAll(self):
        if self.check_all.checkState() == QtCore.Qt.Checked:
            self.check_fatal.setChecked(True)
            self.check_err.setChecked(True)
            self.check_war.setChecked(True)
            self.check_notice.setChecked(True)
            self.check_service.setChecked(True)
        elif self.check_all.checkState() == QtCore.Qt.Unchecked:
            self.check_fatal.setChecked(False)
            self.check_err.setChecked(False)
            self.check_war.setChecked(False)
            self.check_notice.setChecked(False)
            self.check_service.setChecked(False)

    def openMap(self, checked):
        # print("checked: ", checked, self.map_widget)
        if checked:
            self.map_widget.show()
            self.updateMap()
        else:
            self.map_widget.hide()
        self.static_canvas.figure.canvas.draw()

    def updateMidLine(self):
        (xmin,xmax) = self.axs[0].get_xlim()
        tmid = (xmin+xmax)/2.0 
        if len(self.map_select_lines) < 1:
            for ax in self.axs:
                wl = ax.axvline(tmid, color = 'c', linewidth = 10, alpha = 0.5, picker = 10)
                self.map_select_lines.append(wl) 
                self.mid_line_t = num2date(tmid)
        else:
            cur_t = self.map_select_lines[0].get_xdata()[0]
            if type(cur_t) is not datetime:
                cur_t = num2date(cur_t)
            if type(xmin) is not datetime:
                xmin = num2date(xmin)
            if type(xmax) is not datetime:
                xmax = num2date(xmax)
            if cur_t >= xmin and cur_t <= xmax:
                for ln in self.map_select_lines:
                    ln.set_visible(True)
            else:
                for ln in self.map_select_lines:
                    ln.set_visible(True)
                    ln.set_xdata([tmid, tmid])
                    self.mid_line_t = num2date(tmid)

    def openViewer(self, checked):
        if checked:
            if not self.log_widget:
                self.log_widget = LogViewer()
                self.log_widget.setWindowIcon(QtGui.QIcon('rds.ico'))
                self.log_widget.hiddened.connect(self.viewerClosed)
                self.log_widget.moveHereSignal.connect(self.moveHere)
            if self.read_thread.reader:
                self.log_widget.setText(self.read_thread.reader.lines)
            self.log_widget.show()
            self.updateLogView()

        else:
            if self.log_widget:
                self.log_widget.hide() 
    
    def openDataView(self, flag):
        if flag:
            if len(self.dataViews) < 1:
                self.dataViewNewOne(None)
        else:
            if len(self.dataViews) > 0:
                self.data_action.setChecked(True)

    def openJsonView(self, checked):
        if checked:
            if not self.sts_widget:
                self.sts_widget = JsonView()
                self.sts_widget.hiddened.connect(self.jsonViewerClosed)
            self.sts_widget.show()
            self.updateMap()
        else:
            if self.sts_widget:
                self.sts_widget.hide()           
    def openParamView(self, checked):
        if checked:
            if not self.param_widget:
                self.param_widget = SqliteView("")
                self.updateParam()
                self.param_widget.show()
        else:
            if self.param_widget:
                self.param_widget.hide()
    def updateMapSelectLine(self):
        update_line = False
        for ln in self.map_select_lines:
            if self.mid_line_t is not None:
                update_line = True
                ln.set_xdata([self.mid_line_t,self.mid_line_t])
        if update_line:
            self.static_canvas.figure.canvas.draw()

    def mapClosed(self,info):
        # print("hide map")
        self.map_widget.hide()
        # for ln in self.map_select_lines:
        #     ln.set_visible(False)
        self.map_action.setChecked(False)
        self.openMap(False)

    def viewerClosed(self):
        self.view_action.setChecked(False)
        self.openViewer(False)

    def jsonViewerClosed(self, event):
        self.json_action.setChecked(False)
        self.openJsonView(False)

    def closeEvent(self, event):
        self.in_close = True
        self.map_widget.close()
        if self.param_widget:
            self.param_widget.close()
        if self.log_widget:
            self.log_widget.close()
        if self.sts_widget:
            self.sts_widget.close()
        for d in self.dataViews:
            d.close()
        self.close()

    def dataViewClosed(self, other):
        if not self.in_close:
            self.dataViews.remove(other)
            if len(self.dataViews) < 1:
                self.data_action.setChecked(False)
    
    def dataViewNewOne(self, other):
        dataView = DataView()
        dataView.closeMsg.connect(self.dataViewClosed)
        dataView.newOneMsg.connect(self.dataViewNewOne)
        dataView.dataViewMsg.connect(self.updateDataView)
        dataView.setGeometry(850,50,400,900)
        dataView.show()
        self.initDataView(dataView)
        self.dataViews.append(dataView)  
        self.updateDataView(dataView) 

    def initDataView(self, d:DataView):
        print(self.read_thread.robot_keys)
        print(self.read_thread.group_keys)
        d.setSelectionItems(self.read_thread.robot_keys, self.read_thread.group_keys)   

if __name__ == "__main__":
    freeze_support()
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not os.path.exists('log'):
        os.mkdir('log')
    log_name = "log\\loggui_" + str(ts).replace(':','-').replace(' ','_') + ".log"
    logging.basicConfig(filename = log_name,format='[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d][%(funcName)s] %(message)s', level=logging.DEBUG)

    def excepthook(type_, value, traceback_):
        # Print the error and traceback
        traceback.print_exception(type_, value, traceback_) 
        logging.error(traceback.format_exception(type_, value, traceback_))
        QtCore.qFatal('')
    sys.excepthook = excepthook

    try:
        qapp = QtWidgets.QApplication(sys.argv)
        app = ApplicationWindow()
        app.setWindowIcon(QtGui.QIcon('rds.ico'))
        app.show()
        sys.exit(qapp.exec_())
    except:
        logging.error(traceback.format_exc())

