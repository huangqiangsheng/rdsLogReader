from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPlainTextEdit, QVBoxLayout, QHBoxLayout
from PyQt5 import QtGui, QtCore,QtWidgets
import gzip
import re
from rdsLoglib import rbktimetodate

class LogViewer(QWidget):
    hiddened = QtCore.pyqtSignal('PyQt_PyObject')
    moveHereSignal = QtCore.pyqtSignal('PyQt_PyObject')
    def __init__(self):
        super().__init__()
        self.lines = []
        self.title = "LogViewer"
        self.InitWindow()
        self.resize(600,800)
        self.moveHere_flag = False
        self.less_fig=[]

    def InitWindow(self):
        self.setWindowTitle(self.title)
        vbox = QVBoxLayout()
        self.plainText = QPlainTextEdit()
        self.plainText.setPlaceholderText("This is LogViewer")
        self.plainText.setReadOnly(True)
        self.plainText.setUndoRedoEnabled(False)
        self.plainText.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.plainText.setBackgroundVisible(True)
        self.plainText.ensureCursorVisible()
        self.plainText.contextMenuEvent = self.contextMenuEvent
        
        hbox = QHBoxLayout()
        self.find_edit = QtWidgets.QLineEdit()
        self.find_up = QtWidgets.QPushButton("Up")
        self.find_up.clicked.connect(self.findUp)
        self.find_down = QtWidgets.QPushButton("Down")
        self.find_down.clicked.connect(self.findDown)
        self.less_btn = QtWidgets.QPushButton("Less")
        self.less_btn.clicked.connect(self.less)
        self.case_btn = QtWidgets.QPushButton("Ignore \n Case")
        self.case_btn.setCheckable(True)
        self.case_btn.clicked.connect(self.caseChange)
        self.reg_btn = QtWidgets.QPushButton("Disable \n Reg")
        self.reg_btn.setCheckable(True)
        self.reg_btn.clicked.connect(self.regChange)
        hbox.addWidget(self.find_edit)
        hbox.addWidget(self.find_up)
        hbox.addWidget(self.find_down)
        hbox.addWidget(self.less_btn)
        hbox.addWidget(self.case_btn)
        hbox.addWidget(self.reg_btn)
        vbox.addWidget(self.plainText)
        vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.find_cursor = None
        self.find_set_cursor = None
        self.highlightFormat = QtGui.QTextCharFormat()
        self.highlightFormat.setForeground(QtGui.QColor("red"))
        self.plainText.cursorPositionChanged.connect(self.cursorChanged)
        self.last_cursor = None
    def setText(self, lines):
        self.plainText.setPlainText(''.join(lines))    
    def setLineNum(self, ln):
        print("moveHere_flag", self.moveHere_flag)
        if not self.moveHere_flag:
            cursor = QtGui.QTextCursor(self.plainText.document().findBlockByLineNumber(ln))
            self.plainText.setTextCursor(cursor)
        else:
            self.moveHere_flag = False
    def closeEvent(self,event):
        self.hide()
        self.hiddened.emit(True)    
    def readFilies(self,files):
        for file in files:
            if os.path.exists(file):
                if file.endswith(".log"):
                    try:
                        with open(file,'rb') as f:
                            self.readData(f,file)
                    except:
                        continue
                else:
                    try:
                        with gzip.open(file,'rb') as f:
                            self.readData(f, file) 
                    except:
                        continue
        self.setText(self.lines)  

    # def mousePressEvent(self, event):
    #     self.popMenu = self.plainText.createStandardContextMenu()
    #     self.popMenu.addAction('&Move Here',self.moveHere)
    #     cursor = QtGui.QCursor()
    #     self.popMenu.exec_(cursor.pos())   
    
    def contextMenuEvent(self, event):
        popMenu = self.plainText.createStandardContextMenu()
        popMenu.addAction('&Move Here',self.moveHere)
        cursor = QtGui.QCursor()
        popMenu.exec_(cursor.pos()) 

    def moveHere(self):
        cur_cursor = self.plainText.textCursor()
        cur_cursor.select(QtGui.QTextCursor.LineUnderCursor)
        line = cur_cursor.selectedText()
        regex = re.compile("\[(.*?)\].*")
        out = regex.match(line)
        if out:
            self.moveHere_flag = True
            mtime = rbktimetodate(out.group(1))
            self.moveHereSignal.emit(mtime)

    def moveHereWithTime(self, mtime):
        self.moveHereSignal.emit(mtime)

    def readData(self, f, file):
        for line in f.readlines(): 
            try:
                line = line.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    line = line.decode('gbk')
                except UnicodeDecodeError:
                    print("{} {}:{}".format(file,"Skipped due to decoding failure!", line))
                    continue
            self.lines.append(line)        

    def findUp(self):
        searchStr = self.find_edit.text()
        if searchStr != "":
            if self.reg_btn.isChecked():
                searchStr = QtCore.QRegularExpression(searchStr)
            doc = self.plainText.document()
            cur_highlightCursor = self.plainText.textCursor()
            if self.find_cursor:
                if self.find_set_cursor and \
                    self.find_set_cursor.position() == cur_highlightCursor.position():
                    cur_highlightCursor = QtGui.QTextCursor(self.find_cursor)
                    cur_highlightCursor.setPosition(cur_highlightCursor.anchor())                   
            if self.case_btn.isChecked() == False:
                cur_highlightCursor = doc.find(searchStr, cur_highlightCursor, QtGui.QTextDocument.FindBackward)
            else:
                cur_highlightCursor = doc.find(searchStr, cur_highlightCursor, QtGui.QTextDocument.FindBackward|QtGui.QTextDocument.FindCaseSensitively)
            if cur_highlightCursor.position() >= 0:
                if self.find_cursor:
                    fmt = QtGui.QTextCharFormat()
                    self.find_cursor.setCharFormat(fmt)
                cur_highlightCursor.movePosition(QtGui.QTextCursor.NoMove,QtGui.QTextCursor.KeepAnchor)
                cur_highlightCursor.mergeCharFormat(self.highlightFormat)
                self.find_cursor = QtGui.QTextCursor(cur_highlightCursor)
                cur_highlightCursor.setPosition(cur_highlightCursor.anchor())
                self.find_set_cursor = cur_highlightCursor
                self.plainText.setTextCursor(cur_highlightCursor)

    def findDown(self):
        searchStr = self.find_edit.text()
        if searchStr != "":
            if self.reg_btn.isChecked():
                searchStr = QtCore.QRegularExpression(searchStr)
            doc = self.plainText.document()
            cur_highlightCursor = self.plainText.textCursor()
            if self.find_cursor:
                if self.find_set_cursor and \
                    cur_highlightCursor.position() == self.find_set_cursor.position():
                    cur_highlightCursor = QtGui.QTextCursor(self.find_cursor)
                    cur_highlightCursor.clearSelection()
            if self.case_btn.isChecked() == False:
                cur_highlightCursor = doc.find(searchStr, cur_highlightCursor)
            else:
                cur_highlightCursor = doc.find(searchStr, cur_highlightCursor, QtGui.QTextDocument.FindCaseSensitively)
            if cur_highlightCursor.position()>=0:
                if self.find_cursor:
                    fmt = QtGui.QTextCharFormat()
                    self.find_cursor.setCharFormat(fmt)
                cur_highlightCursor.movePosition(QtGui.QTextCursor.NoMove,QtGui.QTextCursor.KeepAnchor)
                cur_highlightCursor.setCharFormat(self.highlightFormat)
                self.find_cursor = QtGui.QTextCursor(cur_highlightCursor)
                cur_highlightCursor.clearSelection()
                self.find_set_cursor = cur_highlightCursor
                self.plainText.setTextCursor(cur_highlightCursor)
                
    def cursorChanged(self):

        fmt= QtGui.QTextBlockFormat()
        fmt.setBackground(QtGui.QColor("light blue"))
        cur_cursor = self.plainText.textCursor()
        cur_cursor.select(QtGui.QTextCursor.LineUnderCursor)
        cur_cursor.setBlockFormat(fmt)
        if self.last_cursor:
            if cur_cursor.blockNumber() != self.last_cursor.blockNumber():
                fmt = QtGui.QTextBlockFormat()
                self.last_cursor.select(QtGui.QTextCursor.LineUnderCursor)
                self.last_cursor.setBlockFormat(fmt)          
        self.last_cursor = self.plainText.textCursor()

    def caseChange(self):
        if self.case_btn.isChecked():
            self.case_btn.setText("Match \n Case")
        else:
            self.case_btn.setText("Ignore \n Case")
    def regChange(self):
        if self.reg_btn.isChecked():
            self.reg_btn.setText("Enable \n Reg")
        else:
            self.reg_btn.setText("Disable \n Reg")
    def less(self):
        searchStr = self.find_edit.text()
        if searchStr == "":
            return
        lines = []
        doc = self.plainText.document()
        if searchStr != "":
            if self.reg_btn.isChecked():
                searchStr = QtCore.QRegularExpression(searchStr)
        if self.case_btn.isChecked() == False:
            cursor = doc.find(searchStr, 0)     
        else:
            cursor = doc.find(searchStr, 0, QtGui.QTextDocument.FindCaseSensitively)
        while cursor.blockNumber() > 0:
            if self.case_btn.isChecked() == False:
                cursor = doc.find(searchStr, cursor)     
            else:
                cursor = doc.find(searchStr, cursor, QtGui.QTextDocument.FindCaseSensitively)    
            if cursor.blockNumber() < 1:
                break
            next_pos = cursor.block().next().position()
            if next_pos < 1:
                break
            lines.append(cursor.block().text()+'\n')
            cursor.setPosition(next_pos)
        print("line size:",len(lines))
        if len(lines) < 1:
            return
        new_lg = LogViewer()
        new_lg.setWindowTitle(self.find_edit.text())
        new_lg.setWindowIcon(QtGui.QIcon('rds.ico'))
        new_lg.moveHereSignal.connect(self.moveHereWithTime)    
        new_lg.setText(lines)
        self.less_fig.append(new_lg)    
        new_lg.show()

if __name__ == "__main__":
    import sys
    import os
    app = QApplication(sys.argv)
    view = LogViewer()
    filenames = ["test1.log"]
    view.readFilies(filenames)
    view.show()
    app.exec_()

