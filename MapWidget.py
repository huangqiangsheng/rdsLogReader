from multiprocessing import set_forkserver_preload
from tkinter.messagebox import NO
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib.lines as lines
import matplotlib.text as mtext
from matplotlib.patches import Circle, Polygon
from PyQt5 import QtGui, QtCore,QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import numpy as np
import json as js
import os
from MyToolBar import MyToolBar, keepRatio, RulerShape
from matplotlib.path import Path
import matplotlib.patches as patches
from matplotlib.textpath import TextPath
import math
import logging
import copy
import time
import random

def GetGlobalPos(p2b, b2g):
    x = p2b[0] * np.cos(b2g[2]) - p2b[1] * np.sin(b2g[2])
    y = p2b[0] * np.sin(b2g[2]) + p2b[1] * np.cos(b2g[2])
    x = x + b2g[0]
    y = y + b2g[1]
    return np.array([x, y])

def normalize_theta(theta):
    if theta >= -math.pi and theta < math.pi:
        return theta
    multiplier = math.floor(theta / (2 * math.pi))
    theta = theta - multiplier * 2 * math.pi
    if theta >= math.pi:
        theta = theta - 2 * math.pi
    if theta < -math.pi:
        theta = theta + 2 * math.pi
    return theta


class RobotModel:
    def __init__(self) -> None:
        self.head = None
        self.tail = None 
        self.width = None
        self.pos = [None,None,None]
        self.name = None
        self.areaName = None
        self.cur_arrow = patches.FancyArrow(0, 0, 0.3, 0,
                                            length_includes_head=True,# 增加的长度包含箭头部分
                                            width=0.05,
                                            head_width=0.1, head_length=0.16, fc='r', ec='b')
        self.cur_arrow.set_zorder(0)
        self.org_arrow_xy = self.cur_arrow.get_xy().copy()

        self.robot_data = lines.Line2D([],[], linestyle = '-', color='k')
        self.robot_data_c0 = lines.Line2D([],[], linestyle = '-', linewidth = 2, color='k')
        self.trajectory = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 2.0, color='m')
        self.trajectory_next = lines.Line2D([],[], linestyle = '', marker = 'o', markersize = 2.0, color='mediumpurple')
        self.robot_text = mtext.Text(0,0, "")

    def updateByPos(self, areaName = None):
        if self.head is None or self.pos[0] is None:
            return
        xdata = [-self.tail, -self.tail, self.head, self.head, -self.tail]
        ydata = [self.width/2, -self.width/2, -self.width/2, self.width/2, self.width/2]
        robot_shape = np.array([xdata, ydata])
        xxdata = [-0.05, 0.05, 0.0, 0.0, 0.0]
        xydata = [0.0, 0.0, 0.0, 0.05, -0.05]
        cross_shape = np.array([xxdata,xydata])

        robot_shape = GetGlobalPos(robot_shape, self.pos)
        self.robot_data.set_xdata(robot_shape[0])
        self.robot_data.set_ydata(robot_shape[1])
        
        cross_shape = GetGlobalPos(cross_shape, self.pos)
        self.robot_data_c0.set_xdata(cross_shape[0])
        self.robot_data_c0.set_ydata(cross_shape[1])

        x0 = self.pos[0] 
        y0 = self.pos[1]
        r0 = self.pos[2]
        data = self.org_arrow_xy.copy()
        tmp_data = data.copy()
        data[:,0]= tmp_data[:,0] * np.cos(r0) - tmp_data[:,1] * np.sin(r0)
        data[:,1] = tmp_data[:,0] * np.sin(r0) + tmp_data[:,1] * np.cos(r0)
        data = data + [x0, y0]
        self.cur_arrow.set_xy(data)

        self.robot_text.set_x(robot_shape[0][0])
        self.robot_text.set_y(robot_shape[1][0])
        print(areaName, self.areaName)
        if areaName is not None:
            show = self.areaName == areaName
            self.robot_text.set_visible(show)
            self.cur_arrow.set_visible(show)
            self.robot_data.set_visible(show)
            self.robot_data_c0.set_visible(show)
            self.trajectory.set_visible(show)
            self.trajectory_next.set_visible(show)
    
    def clear_artist(self):
        self.robot_text.remove()
        self.cur_arrow.remove()
        self.robot_data_c0.remove()
        self.robot_data.remove()

    def readModel(self, name, paths):
        self.name = name
        self.robot_text = mtext.Text(0,0, self.name)
        fname = os.path.join(paths, name)
        fname = os.path.join(fname, "models")
        fname = os.path.join(fname, "robot.model")
        with open(fname, 'r',encoding= 'UTF-8') as fid:
            try:
                model_js = js.load(fid)
            except:
                logging.error("robot model file cannot read!!!")
            # fid.close()
            self.head = None
            self.tail = None 
            self.width = None
            if 'chassis' in model_js:
                self.head = float(model_js['chassis']['head'])
                self.tail = float(model_js['chassis']['tail'])
                self.width = float(model_js['chassis']['width'])
            elif 'deviceTypes' in model_js:
                for device in model_js['deviceTypes']:
                    if device['name'] == 'chassis':
                        for param in device['devices'][0]['deviceParams']:
                            if param['key'] == 'shape':
                                for childparam in param['comboParam']['childParams']:
                                    if childparam['key'] == 'rectangle':
                                        if param['comboParam']['childKey'] == childparam['key']:
                                            for p in childparam['params']:
                                                if p['key'] == 'width':
                                                    self.width = p['doubleValue']
                                                elif p['key'] == 'head':
                                                    self.head = p['doubleValue']
                                                elif p['key'] == 'tail':
                                                    self.tail = p['doubleValue']
                                    elif childparam['key'] == 'circle':
                                        if param['comboParam']['childKey'] == childparam['key']:
                                            for p in childparam['params']:
                                                if p['key'] == 'radius':
                                                    self.width = p['doubleValue']
                                                    self.head = self.width
                                                    self.tail = self.width
            else:
                logging.error('Cannot Open robot.model: ' + name)        

class AdancedBlock:
    def __init__(self) -> None:
        self.className = ""
        self.instanceName = ""
        self.posGroup = []
        self.dir = 0
        self.property = []
        self.desc = []

class AreaData:
    def __init__(self) -> None:
        self.name = ""
        self.lines = []
        self.circles = []
        self.points = []
        self.straights = []
        self.p_names = []
        self.map_x = []
        self.map_y = []
        self.blocks = []
        self.binList = []
class Readmap(QThread):
    signal = pyqtSignal('PyQt_PyObject')
    def __init__(self):
        QThread.__init__(self)
        self.map_name = ''
        self.js = dict()
        self.map_data = dict()
        self.bezier_codes = [ 
            Path.MOVETO,
            Path.CURVE4,
            Path.CURVE4,
            Path.CURVE4,
            ]
        self.straight_codes = [
            Path.MOVETO,
            Path.LINETO ,
        ]
        self.robots = dict()
    # run method gets called when we start the thread
    def run(self):
        fid = open(self.map_name, encoding= 'UTF-8')
        self.js = js.load(fid)
        fid.close()
        self.map_data = dict()
        # print(self.js.keys())
        def addStr(areadata, startPos, endPos):
            x1 = 0
            y1 = 0
            x2 = 0
            y2 = 0
            if 'x' in startPos:
                x1 = startPos['x']
            if 'y' in startPos:
                y1 = startPos['y']
            if 'x' in endPos:
                x2 = endPos['x']
            if 'y' in endPos:
                y2 = endPos['y']
            areadata.straights.append([(x1,y1),(x2,y2)])
        def f3order(p0, p1, p2, p3):
            dt = 0.001
            t = 0
            v = []
            while(t < 1.0):
                s = 1 - t
                x = (p0 * s * s * s
                        + 3.0 * p1 * s * s * t
                        + 3.0 * p2 * s * t * t
                        + p3 * t * t * t)
                v.append(x)
                t = t + dt
            return v 
        def f5order(p0, p1, p2, p3, p4, p5):
            dt = 0.001
            t = 0
            v = []
            while(t < 1.0):
                s = 1 - t
                x = (p0 * s * s * s * s * s 
                        + 5.0 * p1 * s * s * s * s * t
                        + 10.0 * p2 * s * s * s * t * t
                        + 10.0 * p3 * s * s * t * t * t
                        + 5.0 * p4 * s * t *t * t * t
                        + p5 * t * t * t * t * t)
                v.append(x)
                t = t + dt
            return v 
        for area in self.js["areas"]:
            areadata = AreaData()
            print("areaname:",area["name"])
            areadata.name = area["name"]
            self.map_data[area["name"]] = areadata
            logicMap = area["logicalMap"]
            if 'advancedCurves' in logicMap:
                for line in logicMap['advancedCurves']:
                    if line['className'] == 'BezierPath'\
                        or line['className'] == 'DegenerateBezier':
                        x0 = 0
                        y0 = 0
                        x1 = 0
                        y1 = 0
                        x2 = 0
                        y2 = 0
                        x3 = 0
                        y3 = 0
                        if 'x' in line['startPos']['pos']:
                            x0 = line['startPos']['pos']['x']
                        if 'y' in line['startPos']['pos']:
                            y0 = line['startPos']['pos']['y']
                        if 'x' in line['controlPos1']:
                            x1 = line['controlPos1']['x']
                        if 'y' in line['controlPos1']:
                            y1 = line['controlPos1']['y']
                        if 'x' in line['controlPos2']:
                            x2 = line['controlPos2']['x']
                        if 'y' in line['controlPos2']:
                            y2 = line['controlPos2']['y']
                        if 'x' in line['endPos']['pos']:
                            x3 = line['endPos']['pos']['x']
                        if 'y' in line['endPos']['pos']:
                            y3 = line['endPos']['pos']['y']
                        xs = np.array([])
                        ys = np.array([])
                        if line['className'] == 'BezierPath':
                            xs = np.array(f3order(x0, x1, x2, x3))
                            ys = np.array(f3order(y0, y1, y2, y3))
                        elif line['className'] == 'DegenerateBezier':
                            xs = np.array(f5order(x0, x1, x1, x2, x2, x3))
                            ys = np.array(f5order(y0, y1, y1, y2, y2, y3))
                        points = np.vstack((xs,ys))  
                        areadata.lines.append(points.T)
                    elif line['className'] == 'ArcPath':
                        x1 = 0
                        y1 = 0
                        x2 = 0
                        y2 = 0
                        x3 = 0
                        y3 = 0
                        if 'x' in line['startPos']['pos']:
                            x1 = line['startPos']['pos']['x']
                        if 'y' in line['startPos']['pos']:
                            y1 = line['startPos']['pos']['y']
                        if 'x' in line['controlPos1']:
                            x2 = line['controlPos1']['x']
                        if 'y' in line['controlPos1']:
                            y2 = line['controlPos1']['y']
                        if 'x' in line['endPos']['pos']:
                            x3 = line['endPos']['pos']['x']
                        if 'y' in line['endPos']['pos']:
                            y3 = line['endPos']['pos']['y']
                        A = x1*(y2-y3) - y1*(x2-x3)+x2*y3-x3*y2
                        B = (x1*x1 + y1*y1)*(y3-y2)+(x2*x2+y2*y2)*(y1-y3)+(x3*x3+y3*y3)*(y2-y1)
                        C = (x1*x1 + y1*y1)*(x2-x3)+(x2*x2+y2*y2)*(x3-x1)+(x3*x3+y3*y3)*(x1-x2)
                        D = (x1*x1 + y1*y1)*(x3*y2-x2*y3)+(x2*x2+y2*y2)*(x1*y3-x3*y1)+(x3*x3+y3*y3)*(x2*y1-x1*y2)
                        if abs(A) > 1e-12:
                            x = -B/2/A
                            y = -C/2/A
                            r = math.sqrt((B*B+C*C-4*A*D)/(4*A*A))
                            theta1 = math.atan2(y1-y,x1-x)
                            theta3 = math.atan2(y3-y,x3-x)
                            v1 = np.array([x2-x1,y2-y1])
                            v2 = np.array([x3-x2,y3-y2])
                            flag = float(np.cross(v1,v2))
                            if flag >= 0:
                                areadata.circles.append([x, y, r, np.rad2deg(theta1), np.rad2deg(theta3)])
                            else:
                                areadata.circles.append([x, y, r, np.rad2deg(theta3), np.rad2deg(theta1)])
                        else:
                            areadata.straights.append([(x1,y1),(x3,y3)])
                    elif line['className'] == 'StraightPath':
                        addStr(areadata, line['startPos']['pos'],line['endPos']['pos'])
            if 'primitiveList' in logicMap:
                for line in logicMap['primitiveList']:
                    if line['className'] == 'RoundLine':
                        cL = line['controlPosList']
                        critical_dist = math.hypot(cL[1]['x'] - cL[3]['x'], cL[1]['y'] - cL[3]['y'])
                        angle1 = math.atan2(cL[0]['y'] - cL[1]['y'], cL[0]['x'] - cL[1]['x'])
                        angle2 = math.atan2(cL[3]['y'] - cL[1]['y'], cL[3]['x'] - cL[1]['x'])
                        angle3 = math.atan2(cL[2]['y'] - cL[1]['y'], cL[2]['x'] - cL[1]['x'])
                        delta_angle = normalize_theta(angle2 - angle1)
                        delta_angle2 = normalize_theta(angle3 - angle2)
                        if critical_dist < 0.0001 or math.fabs(math.fabs(delta_angle) - math.fabs(delta_angle2) > 0.1):
                            addStr(line['startPos']['pos'],line['endPos']['pos'])                     
                        else:
                            addStr(line['startPos']['pos'],cL[0])
                            addStr(cL[2],line['endPos']['pos'])
                            r0 = math.hypot(cL[1]['x'] - cL[0]['x'], cL[1]['y'] - cL[0]['y'])
                            r1 = math.hypot(cL[1]['x'] - cL[2]['x'], cL[1]['y'] - cL[2]['y'])
                            r = (r0 + r1)/2.0
                            if angle1 < angle3:
                                areadata.circles.append([cL[1]['x'], cL[1]['y'], r, np.rad2deg(angle1), np.rad2deg(angle3)])
                            else:
                                areadata.circles.append([cL[1]['x'], cL[1]['y'], r, np.rad2deg(angle3), np.rad2deg(angle1)])
            if 'advancedPoints' in logicMap:
                for pt in logicMap['advancedPoints']:
                    x0 = 0
                    y0 = 0 
                    theta = 0
                    if 'x' in pt['pos']:
                        x0 = pt['pos']['x']
                    if 'y' in pt['pos']:
                        y0 = pt['pos']['y']
                    if 'dir' in pt:
                        theta = pt['dir']
                    if  'ignoreDir' in pt:
                        if pt['ignoreDir'] == True:
                            theta = None
                    areadata.points.append([x0,y0,theta])
                    areadata.p_names.append([pt['instanceName']])
                    areadata.map_x.append(x0)
                    areadata.map_y.append(y0)
            if 'advancedBlocks' in logicMap:
                for b in logicMap['advancedBlocks']:
                    ab = AdancedBlock()
                    ab.className = b['className']
                    ab.instanceName = b['instanceName']
                    for p in b['posGroup']:
                        x = p.get('x',0)
                        y = p.get('y',0)
                        ab.posGroup.append([x,y])
                    ab.dir = b['dir']
                    ab.desc = b['desc']
                    areadata.blocks.append(ab)
            print('blocks size', areadata.name, len(areadata.blocks))
        for k in self.robots.keys():
            self.robots[k].clear_artist()
        self.robots.clear()
        for rs in self.js["robotGroup"]:
            for r in rs["robot"]:
                name = r["id"]
                robot = RobotModel()
                paths = os.path.dirname(self.map_name)
                paths = os.path.join(paths, "robots")
                robot.readModel(name, paths)
                self.robots[name] = robot
        self.signal.emit(self.map_name)

class PointWidget(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self, parent = None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.x_label = QtWidgets.QLabel('x(m)')
        self.y_label = QtWidgets.QLabel('y(m)')
        valid = QtGui.QDoubleValidator()
        self.x_edit = QtWidgets.QLineEdit()
        self.x_edit.setValidator(valid)
        self.y_edit = QtWidgets.QLineEdit()
        self.y_edit.setValidator(valid)
        self.x_input = QtWidgets.QFormLayout()
        self.x_input.addRow(self.x_label,self.x_edit)
        self.y_input = QtWidgets.QFormLayout()
        self.y_input.addRow(self.y_label,self.y_edit)
        self.btn = QtWidgets.QPushButton("Yes")
        self.btn.clicked.connect(self.getData)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addLayout(self.x_input)
        vbox.addLayout(self.y_input)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Point Input")

    def getData(self):
        try:
            x = float(self.x_edit.text())
            y = float(self.y_edit.text())
            self.hide()
            self.getdata.emit([x,y])
        except:
            pass

class LineWidget(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self, parent = None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.groupBox1 = QtWidgets.QGroupBox('P1')
        x_label = QtWidgets.QLabel('x(m)')
        y_label = QtWidgets.QLabel('y(m)')
        valid = QtGui.QDoubleValidator()
        self.x_edit1 = QtWidgets.QLineEdit()
        self.x_edit1.setValidator(valid)
        self.y_edit1 = QtWidgets.QLineEdit()
        self.y_edit1.setValidator(valid)
        x_input = QtWidgets.QFormLayout()
        x_input.addRow(x_label,self.x_edit1)
        y_input = QtWidgets.QFormLayout()
        y_input.addRow(y_label,self.y_edit1)
        vbox1 = QtWidgets.QVBoxLayout()
        vbox1.addLayout(x_input)
        vbox1.addLayout(y_input)
        self.groupBox1.setLayout(vbox1)
        
        self.groupBox2 = QtWidgets.QGroupBox('P2')
        x_label = QtWidgets.QLabel('x(m)')
        y_label = QtWidgets.QLabel('y(m)')
        valid = QtGui.QDoubleValidator()
        self.x_edit2 = QtWidgets.QLineEdit()
        self.x_edit2.setValidator(valid)
        self.y_edit2 = QtWidgets.QLineEdit()
        self.y_edit2.setValidator(valid)
        x_input = QtWidgets.QFormLayout()
        x_input.addRow(x_label,self.x_edit2)
        y_input = QtWidgets.QFormLayout()
        y_input.addRow(y_label,self.y_edit2)
        vbox2 = QtWidgets.QVBoxLayout()
        vbox2.addLayout(x_input)
        vbox2.addLayout(y_input)
        self.groupBox2.setLayout(vbox2)

        vbox = QtWidgets.QVBoxLayout(self)
        self.btn = QtWidgets.QPushButton("Yes") 
        self.btn.clicked.connect(self.getData)
        vbox.addWidget(self.groupBox1)
        vbox.addWidget(self.groupBox2)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Line Input")

    def getData(self):
        try:
            x1 = float(self.x_edit1.text())
            y1 = float(self.y_edit1.text())
            x2 = float(self.x_edit2.text())
            y2 = float(self.y_edit2.text())
            self.hide()
            self.getdata.emit([[x1,y1],[x2,y2]])
        except:
            pass

class CurveWidget(QtWidgets.QWidget):
    getdata = pyqtSignal('PyQt_PyObject')
    def __init__(self, parent = None):
        super(QtWidgets.QWidget, self).__init__(parent)
        self.data_label = QtWidgets.QLabel('Script: x,y,linestype,marker,markersize,color:')
        self.data_edit = QtWidgets.QTextEdit()
        self.btn = QtWidgets.QPushButton("Yes")
        self.btn.clicked.connect(self.getData)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.data_label)
        vbox.addWidget(self.data_edit)
        vbox.addWidget(self.btn)
        self.setWindowTitle("Curve Input")
        self.show()

    def getData(self):
        code = self.data_edit.toPlainText()
        try:
            l = locals()
            exec(code,globals(),l)
            self.hide()
            self.getdata.emit([l['x'],l['y'],
            l.get('linestyle','--'),
            l.get('marker','.'), 
            l.get('markersize',6),
            l.get('color','r')])
        except Exception as err:
            print(err.args)
            pass



class MapWidget(QtWidgets.QWidget):
    dropped = pyqtSignal('PyQt_PyObject')
    hiddened = pyqtSignal('PyQt_PyObject')
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('MapViewer')
        self.map_name = None
        self.model_name = None
        self.cp_name = None
        self.draw_size = [] #xmin xmax ymin ymax
        self.check_draw_flag = False
        self.fig_ratio = 1.0
        self.setAcceptDrops(True)
        self.dropped.connect(self.dragFiles)
        self.read_map = Readmap()
        self.read_map.signal.connect(self.readMapFinished)
        self.setupUI()
        self.pointLists = dict()
        self.lineLists = dict()
        self.mapData = dict()
        self.cur_area = None

    def setupUI(self):
        self.static_canvas = FigureCanvas(Figure(figsize=(5,5)))
        self.static_canvas.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.static_canvas.figure.subplots_adjust(left = 0.0, right = 1.0, bottom = 0.0, top = 1.0)
        self.static_canvas.figure.tight_layout()
        self.ax= self.static_canvas.figure.subplots(1, 1)
        self.ruler = RulerShape()
        self.ruler.add_ruler(self.ax)
        MyToolBar.home = self.toolbarHome
        self.toolbar = MyToolBar(self.static_canvas, self, ruler = self.ruler)
        self.toolbar.fig_ratio = 1
        self.userToolbar = QtWidgets.QToolBar(self)
        self.autoMap = QtWidgets.QAction("AUTO", self.userToolbar)
        self.autoMap.setCheckable(True)
        self.autoMap.toggled.connect(self.changeAutoMap)
        self.smap_action = QtWidgets.QAction("SCENE", self.userToolbar)
        self.smap_action.triggered.connect(self.openMap)

        self.draw_point = QtWidgets.QAction("POINT", self.userToolbar)
        self.draw_point.triggered.connect(self.addPoint)
        self.draw_line = QtWidgets.QAction("LINE", self.userToolbar)
        self.draw_line.triggered.connect(self.addLine)
        self.draw_curve = QtWidgets.QAction("CURVE", self.userToolbar)
        self.draw_curve.triggered.connect(self.addCurve)
        self.draw_clear = QtWidgets.QAction("CLEAR", self.userToolbar)
        self.draw_clear.triggered.connect(self.drawClear)

        self.userToolbar.addActions([self.autoMap, self.smap_action])
        self.userToolbar.addSeparator()
        self.userToolbar.addActions([self.draw_point, self.draw_line, self.draw_curve, self.draw_clear])

        self.scenceToolBar = QtWidgets.QToolBar(self)
        self.areaGroup = QtWidgets.QActionGroup(self)
        # self.scenceToolBar.addAction(self.areaGroup)

        self.getPoint = PointWidget(self)
        self.getPoint.getdata.connect(self.getPointData)
        self.getPoint.hide()
        self.getPoint.setWindowFlags(Qt.Window)
        self.getLine = LineWidget(self)
        self.getLine.getdata.connect(self.getLineData)
        self.getLine.hide()
        self.getLine.setWindowFlags(Qt.Window)
        self.getCurve = CurveWidget(self)
        self.getCurve.getdata.connect(self.getCurveData)
        self.getCurve.hide()
        self.getCurve.setWindowFlags(Qt.Window)
        self.autoMap.setChecked(True)
        self.fig_layout = QtWidgets.QVBoxLayout(self)
        self.fig_layout.addWidget(self.toolbar)
        self.fig_layout.addWidget(self.scenceToolBar)
        self.fig_layout.addWidget(self.userToolbar)
        self.fig_layout.addWidget(self.static_canvas)
        self.static_canvas.mpl_connect('resize_event', self.resize_fig)

        
    def changeAutoMap(self):
        flag =  not self.autoMap.isChecked()
        self.smap_action.setEnabled(flag)

    def openMap(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtCore.Qt.WindowStaysOnTopHint
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,"选取scene文件", "","scene Files (*.scene);;All Files (*)", options=options)
        if filename:
            self.map_name = filename
            self.read_map.map_name = self.map_name
            print("start openMap")
            self.read_map.start()

    def addPoint(self):
        self.getPoint.show()

    def getPointData(self, event):
        point = lines.Line2D([],[], linestyle = '', marker = 'x', markersize = 8.0, color='r')
        point.set_xdata(event[0])
        point.set_ydata(event[1])
        id = str(int(round(time.time()*1000)))
        if id not in self.pointLists or self.pointLists[id] is None:
            self.pointLists[id] = point
            self.ax.add_line(self.pointLists[id])
            self.static_canvas.figure.canvas.draw() 

    def addLine(self):
        self.getLine.show()
    
    def addCurve(self):
        self.getCurve.show()

    def getLineData(self, event):
        l = lines.Line2D([],[], linestyle = '--', marker = '.', markersize = 6.0, color='r')
        l.set_xdata([event[0][0],event[1][0]])
        l.set_ydata([event[0][1],event[1][1]])
        id = str(int(round(time.time()*1000)))
        if id not in self.lineLists or self.lineLists[id] is None:
            self.lineLists[id] = l
            self.ax.add_line(self.lineLists[id])
            self.static_canvas.figure.canvas.draw() 

    def getCurveData(self, event):
        l = lines.Line2D([],[], linestyle = event[2], marker = event[3], markersize = event[4], color=event[5])
        l.set_xdata(event[0])
        l.set_ydata(event[1])     
        id = str(int(round(time.time()*1000)))
        if id not in self.lineLists or self.lineLists[id] is None:
            self.lineLists[id] = l
            self.ax.add_line(self.lineLists[id])
            self.static_canvas.figure.canvas.draw()

    def drawClear(self):
        for p in self.pointLists:
            if self.pointLists[p] is not None:
                self.pointLists[p].remove()
                self.pointLists[p] = None
        for l in self.lineLists:
            if self.lineLists[l] is not None:
                self.lineLists[l].remove()
                self.lineLists[l] = None
        self.static_canvas.figure.canvas.draw()    

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.hide()
        self.hiddened.emit(True)
        return super().closeEvent(a0)

    def toolbarHome(self, *args, **kwargs):
        if len(self.draw_size) == 4:
            xmin, xmax, ymin ,ymax = keepRatio(self.draw_size[0], self.draw_size[1], self.draw_size[2], self.draw_size[3], self.fig_ratio)
            self.ax.set_xlim(xmin,xmax)
            self.ax.set_ylim(ymin,ymax)
            self.static_canvas.figure.canvas.draw()

    def resize_fig(self, event):
        ratio = event.width/event.height
        self.fig_ratio = ratio
        self.toolbar.fig_ratio = ratio
        (xmin, xmax) = self.ax.get_xlim()
        (ymin, ymax) = self.ax.get_ylim()
        bigger = True
        if len(self.draw_size) == 4:
            factor = 1.5
            if not(xmin > self.draw_size[0]*factor or xmax < self.draw_size[1]*factor or ymin > self.draw_size[2]*factor or ymax < self.draw_size[3]*factor):
                bigger = False
        xmin, xmax, ymin ,ymax = keepRatio(xmin, xmax, ymin, ymax, ratio, bigger)
        self.ax.set_xlim(xmin,xmax)
        self.ax.set_ylim(ymin,ymax)
        self.static_canvas.figure.canvas.draw()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.dropped.emit(links)
        else:
            event.ignore()

    def dragFiles(self,files):
        new_map = False
        for file in files:
            if file and os.path.exists(file):
                print(file)
                if self.smap_action.isEnabled() and os.path.splitext(file)[1] == ".scene":
                    self.map_name = file
                    new_map = True
        if new_map and self.map_name:
            self.read_map.map_name = self.map_name
            print("start drag")
            self.read_map.start()

    def readFiles(self,files):
        new_map = False
        for file in files:
            if file and os.path.exists(file):
                if not self.smap_action.isEnabled() and os.path.splitext(file)[1] == ".scene":
                    if file != self.map_name:
                        self.map_name = file
                        new_map = True
                    print("{} {}".format(file != self.map_name, new_map))

        if new_map and self.map_name:
            self.read_map.map_name = self.map_name
            print("start here!!!")
            self.read_map.start()

    def changeArea(self, event):
        for a in self.areaGroup.actions():
            if a.isChecked():
                self.cur_area = a.text()
        self.autoUpdateArea()

    def autoUpdateArea(self):
        for k in self.mapData:
            show =  k == self.cur_area
            print("mapData:", self.cur_area, k, show)
            for e in self.mapData[k]:
                e.set_visible(show)

        map_data = self.read_map.map_data[self.cur_area]
        xmin = min(map_data.map_x) if len(map_data.map_x) > 0 else 0
        xmax = max(map_data.map_x) if len(map_data.map_x) > 0 else 0
        ymin = min(map_data.map_y) if len(map_data.map_y) > 0 else 0
        ymax = max(map_data.map_y) if len(map_data.map_y) > 0 else 0
        print(xmin, xmax, ymin, ymax)
        if xmax - xmin > ymax - ymin:
            ds = xmax - xmin - ymax + ymin
            ymax = ymax + ds /2.0
            ymin = ymin - ds /2.0
        else:
            ds = ymax - ymin - xmax + xmin
            xmax = xmax + ds /2.0
            xmin = xmin - ds /2.0
        map_size = xmax - xmin
        print(xmin, xmax, ymin, ymax)
        xmin = xmin - map_size * 0.1
        xmax = xmax + map_size * 0.1
        ymin = ymin - map_size * 0.1
        ymax = ymax + map_size * 0.1
        self.draw_size = [xmin, xmax, ymin, ymax]
        # print(self.draw_size[1] - self.draw_size[0], self.draw_size[3] - self.draw_size[2])
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(ymin, ymax)
        for name in self.read_map.robots:
            self.read_map.robots[name].updateByPos(self.cur_area)
        self.static_canvas.figure.canvas.draw()

    def readMapFinished(self, result):
        if len(self.read_map.map_data) > 0:
            self.ax.grid(True)
            self.ax.axis('auto')
            [p.remove() for p in reversed(self.ax.patches)]
            [p.remove() for p in reversed(self.ax.texts)]
            [p.remove() for p in reversed(self.ax.lines)]
            self.ruler.clear_rulers()
            self.ruler.add_ruler(self.ax)
            self.mapData = dict()
            for area_name in self.read_map.map_data:
                map_data = self.read_map.map_data[area_name]
                self.mapData[area_name] = []
                for line in map_data.lines:
                    path = Polygon(line, closed=False, facecolor='none', edgecolor='orange', lw=1)
                    self.mapData[area_name].append(path)
                    self.ax.add_patch(path)
                for circle in map_data.circles:
                    wedge = patches.Arc([circle[0], circle[1]], circle[2]*2, circle[2]*2, 0, circle[3], circle[4], facecolor = 'none', ec="orange", lw = 3)
                    self.mapData[area_name].append(wedge)
                    self.ax.add_patch(wedge)
                for vert in map_data.straights:
                    path = Path(vert, self.read_map.straight_codes)
                    patch = patches.PathPatch(path, facecolor='none', edgecolor='orange', lw=3)
                    self.mapData[area_name].append(patch)
                    self.ax.add_patch(patch)
                for b in map_data.blocks:
                    pass
                pr = 0.25
                for (pt,name) in zip(map_data.points, map_data.p_names):
                    circle = patches.Circle((pt[0], pt[1]), pr, facecolor='orange',
                    edgecolor=(0, 0.8, 0.8), linewidth=3, alpha=0.5)
                    self.mapData[area_name].append(circle)
                    self.ax.add_patch(circle)
                    text_path = TextPath((pt[0],pt[1]), name[0], size = 0.2)
                    text_path = patches.PathPatch(text_path, ec="none", lw=3, fc="k")
                    self.mapData[area_name].append(text_path)
                    self.ax.add_patch(text_path)
                    if pt[2] != None:
                        arrow = patches.Arrow(pt[0],pt[1], pr * np.cos(pt[2]), pr*np.sin(pt[2]), pr)
                        self.mapData[area_name].append(arrow)
                        self.ax.add_patch(arrow)

                tmp_action = QtWidgets.QAction(area_name, self.scenceToolBar)
                tmp_action.triggered.connect(self.changeArea)
                self.scenceToolBar.addAction(tmp_action)
                self.areaGroup.addAction(tmp_action)
                tmp_action.setCheckable(True)

                if self.cur_area is None:
                    self.cur_area = area_name
                if area_name is self.cur_area:
                    tmp_action.setChecked(True)
            self.autoUpdateArea()
            ## model
            for k in self.read_map.robots.keys():
                r = self.read_map.robots[k]
                if r.pos[0] is None:
                    r.pos[0] = random.uniform(self.draw_size[0],  self.draw_size[1])
                    r.pos[1] = random.uniform(self.draw_size[2],  self.draw_size[3])
                    r.pos[2] = random.uniform(-3.14,  3.14)
                if r.areaName is None:
                    r.areaName = self.cur_area
                r.updateByPos(self.cur_area)
                self.ax.add_line(r.robot_data)
                self.ax.add_line(r.robot_data_c0)
                self.ax.add_patch(r.cur_arrow) #add robot arrow again
                self.ax.add_artist(r.robot_text)
                self.ax.add_line(r.trajectory)
                self.ax.add_line(r.trajectory_next)

            self.setWindowTitle("{} : {}".format('MapViewer', os.path.split(self.map_name)[1]))
            font = QtGui.QFont()
            font.setBold(True)
            self.smap_action.setFont(font)
            self.static_canvas.figure.canvas.draw()
    
    def readtrajectory(self, name, areaName, x, y, xn, yn, x0, y0, r0):
        if name in self.read_map.robots:
            r = self.read_map.robots[name]
            r.areaName = areaName
            r.trajectory.set_xdata(x)
            r.trajectory.set_ydata(y)
            r.trajectory_next.set_xdata(xn)
            r.trajectory_next.set_ydata(yn)
            r.pos[0] = x0
            r.pos[1] = y0
            r.pos[2] = r0
            r.updateByPos(self.cur_area)
            if len(self.draw_size) != 4:
                xmax = max(x) + 10 
                xmin = min(x) - 10
                ymax = max(y) + 10
                ymin = min(y) - 10
                self.draw_size = [xmin,xmax, ymin, ymax]
                self.ax.set_xlim(xmin, xmax)
                self.ax.set_ylim(ymin, ymax)

    def redraw(self):
        self.static_canvas.figure.canvas.draw()
    
    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        return super().closeEvent(a0)

if __name__ == '__main__':
    import sys
    import os
    app = QtWidgets.QApplication(sys.argv)
    form = MapWidget()
    form.show()
    app.exec_()
