#!/usr/bin/python3
# -*- coding: utf-8 -*-
### Axel Schneider 2017###
# gist: https://gist.github.com/Axel-Erfurt/ae983df9f65bef0b82a9a3a83a00014a

from PyQt5 import QtSql, QtPrintSupport
from PyQt5.QtGui import QTextDocument, QIcon, QTextCursor, QTextTableFormat
from PyQt5.QtCore import QFileInfo, Qt, QSettings, QSize, QFile, QTextStream, QItemSelectionModel, QVariant
from PyQt5.QtWidgets import (QMainWindow, QTableView, QDialog, QGridLayout, QHBoxLayout, QPushButton, QAbstractItemView,
                                                            QLineEdit, QWidget, QFileDialog, QComboBox, QMessageBox, QApplication)
import sqlite3
import csv
import pandas
###################################
btnWidth = 110
btnHeight = 22
class SqliteView(QMainWindow):
    def __init__(self, parent=None):
        super(SqliteView, self).__init__()
        self.setObjectName("SqliteViewer")
        root = QFileInfo(__file__).absolutePath()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.settings = QSettings('Axel Schneider', self.objectName())
        self.viewer = QTableView()

        self.viewer.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.viewer.setSelectionMode(QAbstractItemView.SingleSelection)
        self.viewer.setDragEnabled(True)
        self.viewer.setDragDropMode(QAbstractItemView.InternalMove)
        self.viewer.setDragDropOverwriteMode(False)

#        self.viewer.rowMoved.connect(self.is)

        self.viewer.verticalHeader().setSectionsMovable(True)
        self.viewer.verticalHeader().setDragEnabled(True)
        self.viewer.verticalHeader().setDragDropMode(QAbstractItemView.InternalMove)
        self.editors = []
        self.db = QtSql.QSqlDatabase.addDatabase('QSQLITE')
        self.model = QtSql.QSqlTableModel()
        self.delrow = -1
        self.dbfile = ""
        self.tablename = ""
        self.headers = []
        self.results = ""
        self.mycolumn = 0
        self.viewer.verticalHeader().setVisible(False)
        self.setStyleSheet(stylesheet(self))
        self.viewer.setModel(self.model)
        self.viewer.clicked.connect(self.findrow)
        self.viewer.selectionModel().selectionChanged.connect(self.getCellText)
        
        self.dlg = QDialog()
        self.layout = QGridLayout()
        self.layout.addWidget(self.viewer,0, 0, 1, 4)

        self.myWidget = QWidget()
        self.myWidget.setLayout(self.layout)

        self.createToolbar()
        self.statusBar().showMessage("Ready")
        self.setCentralWidget(self.myWidget)
        self.setWindowIcon(QIcon.fromTheme("office-database"))
        self.setGeometry(20,20,600,450)
        self.setWindowTitle("SqliteViewer")
        self.readSettings()
        self.msg("Ready")
        self.viewer.setFocus()

    def createToolbar(self):
        self.actionOpen = QPushButton("Open DB")
        self.actionOpen.clicked.connect(self.fileOpen)
        icon = QIcon.fromTheme("document-open")
        self.actionOpen.setShortcut("Ctrl+O")
        self.actionOpen.setShortcutEnabled(True)
        self.actionOpen.setIcon(icon)
        self.actionOpen.setObjectName("actionOpen")
        self.actionOpen.setStatusTip("Open Database")
        self.actionOpen.setToolTip("Open Database")

        ### first row as headers
        self.actionHeaders = QPushButton()
        icon = QIcon.fromTheme("ok")
        self.actionHeaders.setIcon(icon)
        self.actionHeaders.setToolTip("selected row to headers")
        self.actionHeaders.setShortcut("F5")
        self.actionHeaders.setShortcutEnabled(True)
        self.actionHeaders.setStatusTip("selected row to headers")


        ###############################
        self.tb = self.addToolBar("ToolBar")
        self.tb.setIconSize(QSize(16, 16))
        self.tb.setMovable(False)
        self.tb.addWidget(self.actionOpen)
        ### sep
        self.tb.addSeparator()
        self.tb.addSeparator()
        ### popupMenu
        self.pop = QComboBox()
        self.pop.setFixedWidth(200)
        self.pop.currentIndexChanged.connect(self.setTableName)
        self.tb.addWidget(self.pop)
        self.addToolBar(self.tb)

    def findCell(self):
        self.viewer.clearSelection()
        findText = self.findfield.text()
        for i in range(self.viewer.model().columnCount()):
            indexes = self.viewer.model().match(self.viewer.model().index(0, i), Qt.DisplayRole, findText, -1,  Qt.MatchContains)
            for ix in indexes:
                self.viewer.selectRow(ix.row())

    def toggleVerticalHeaders(self):
        if self.viewer.verticalHeader().isVisible() == False:
            self.viewer.verticalHeader().setVisible(True)
            icon = QIcon.fromTheme("go-last-symbolic")
            self.actionHide.setIcon(icon)
        else:
            self.viewer.verticalHeader().setVisible(False)
            icon = QIcon.fromTheme("go-first-symbolic")
            self.actionHide.setIcon(icon)

    def fileOpen(self):
        tablelist = []
        fileName, _ = QFileDialog.getOpenFileName(None, "Open Database File", "/home/brian/Dokumente/DB", "DB (*.sqlite *.db *.sql3);; All Files (*.*)")
        if fileName:
            self.db.close()
            self.dbfile = fileName
            conn = sqlite3.connect(self.dbfile)
            cur = conn.cursor()
            res = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            for name in res:
                print (name[0])
                tablelist.append(name[0])
        self.db.setDatabaseName(self.dbfile)
        self.db.open()
        self.fillComboBox(tablelist)
        self.msg("please choose Table from the ComboBox")

    def fileOpenStartup(self, fileName):
        tablelist = []
        if fileName:
            self.db.close()
            self.dbfile = fileName
            conn = sqlite3.connect(self.dbfile)
            cur = conn.cursor()
            res = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            for name in res:
                print (name[0])
                tablelist.append(name[0])
        self.db.setDatabaseName(self.dbfile)
        self.db.open()
        self.fillComboBox(tablelist)
        self.msg("please choose Table from the ComboBox")

    def importCSV(self):
        csvfile, _ = QFileDialog.getOpenFileName(None, "Open CSV File", "", "CSV (*.csv *.tsv *.txt)")
        if csvfile:
            filename = csvfile.rpartition("/")[2].replace(".csv", "")
            print(filename)
            sqlfile, _ = QFileDialog.getSaveFileName(None, "Save Database File", "/tmp/" + filename + ".sqlite", "SQLite (*.sqlite)")
            if sqlfile:
                if QFile.exists(sqlfile):
                    QFile.remove(sqlfile)
                con = sqlite3.connect(sqlfile)
                cur = con.cursor()
            file = QFile(csvfile)
            if not file.open(QFile.ReadOnly | QFile.Text):
                QMessageBox.warning(self, "Meldung",
                        "Cannot read file %s:\n%s." % (fileName, file.errorString()))
                return
            infile = QTextStream(file)
            mytext = infile.readLine()

        ### ask for header
            ret = QMessageBox.question(self, "SQLiteViewer Message",
                    "use this line as header?\n\n" + mytext,
                    QMessageBox.Ok | QMessageBox.No, defaultButton = QMessageBox.Ok)
            if ret == QMessageBox.Ok:
                df = pandas.read_csv(csvfile, encoding = 'utf-8', delimiter = '\t')
            if ret == QMessageBox.No:
                df = pandas.read_csv(csvfile, encoding = 'utf-8', delimiter = '\t', header=None)
        df.to_sql(filename, con, if_exists='append', index=False)
        self.fileOpenStartup(sqlfile)

    def fileSaveTab(self):
        if not self.model.rowCount() == 0:
            self.msg("exporting Table")
            conn=sqlite3.connect(self.dbfile)
            c=conn.cursor()
            data = c.execute("SELECT * FROM " + self.tablename)
            self.headers = [description[0] for description in c.description]
            fileName, _ = QFileDialog.getSaveFileName(None, "Export Table to CSV", self.tablename + ".tsv", "CSV Files (*.csv *.tsv)")
            if fileName:
                with open(fileName, 'w') as f:
                    writer = csv.writer(f, delimiter = '\t')
                    writer.writerow(self.headers)
                    writer.writerows(data)
        else:
            self.msg("nothing to export")

    def setAutoWidth(self):
        self.viewer.resizeColumnsToContents()

    def fillComboBox(self, tablelist):
        self.pop.clear()
        self.pop.insertItem(0, "choose Table ...")
        self.pop.setCurrentIndex(0)
        for row in tablelist:
            self.pop.insertItem(self.pop.count(), row)
        if self.pop.count() > 1:
            self.pop.setCurrentIndex(1)
            self.setTableName()

    def fileSaveComma(self):
        if not self.model.rowCount() == 0:
            self.msg("exporting Table")
            conn=sqlite3.connect(self.dbfile)
            c=conn.cursor()
            data = c.execute("SELECT * FROM " + self.tablename)
            headers = [description[0] for description in c.description]
            fileName, _ = QFileDialog.getSaveFileName(None, "Export Table to CSV", self.tablename + ".csv", "CSV Files (*.csv)")
            if fileName:
                with open(fileName, 'w') as f:
                    writer = csv.writer(f, delimiter = ',')
                    writer.writerow(headers)
                    writer.writerows(data)
        else:
            self.msg("nothing to export")

    def getCellText(self):
        if self.viewer.selectionModel().hasSelection():
            col = self.selectedColumn()
            item = self.viewer.selectedIndexes()[0]
            row = self.selectedRow()
            print(f"GetCellText: column: {col}, row: {row}, item: {item.data()}, item.column:{item.column()}")
            item = self.viewer.selectedIndexes()[0]
            if not item == None:
                name = item.data()
            else:
                name = ""
            self.editors[self.selectedColumn()].setText(str(name))
        else:
            self.editors[self.selectedColumn()].clear()

    def searchCell(self, column):
        print(f"searchCell: column: {column}")
        if(self.editors[column].text() == ""):
            self.model.setFilter("")
            self.model.select()
            return
        column_name = self.model.record().fieldName(column)
        self.model.setFilter(f"{column_name} LIKE '%{self.editors[column].text()}%'")
        select_result = self.model.select()
        print(f"searchCell: column: {column}, column_name: {column_name}, search result: {select_result}")
    def setTableName(self):
        if not self.pop.currentText() == "choose Table ...":
            self.tablename = self.pop.currentText()
            print("DB is:", self.dbfile)
            self.msg("initialize")
            self.initializeModel()

    def initializeModel(self):
        print("Table selected:", self.tablename)
        self.model.setTable(self.tablename)
        self.model.setEditStrategy(QtSql.QSqlTableModel.OnFieldChange)
        self.model.select()
        self.setAutoWidth()
        self.msg(self.tablename + " loaded *** " + str(self.model.rowCount()) + " records")
        # add search edit fields
        search_row = QHBoxLayout()
        search_row.setSpacing(0)
        search_row.setStretch(0, 0) # no spacing
        self.editors= []
        # no spacing
        for i in range(self.model.columnCount()):
            self.editors.append(QLineEdit())
            self.editors[i].setFixedWidth(self.viewer.columnWidth(i))
            search_row.addWidget(self.editors[i])
            # https://stackoverflow.com/a/2295372/7724731
            self.editors[i].returnPressed.connect(lambda i=i: self.searchCell(i)) # i=i force early binding
        self.layout.addLayout(search_row, 1, 0, 1, 2)
        
    def findrow(self, i):
        self.delrow = i.row()

    def selectedRow(self):
        if self.viewer.selectionModel().hasSelection():
            row =  self.viewer.selectionModel().selectedIndexes()[0].row()
            return int(row)

    def selectedColumn(self):
        if self.viewer.selectionModel().hasSelection():
            for index in self.viewer.selectionModel().selectedIndexes():
                print(f"index: {index.row()}, {index.column()}")
            column =  self.viewer.selectionModel().selectedIndexes()[0].column()
            return int(column)

    def closeEvent(self, e):
        self.writeSettings()
        e.accept()

    def readSettings(self):
        print("reading settings")
        if self.settings.contains('geometry'):
            self.setGeometry(self.settings.value('geometry'))

    def writeSettings(self):
        print("writing settings")
        self.settings.setValue('geometry', self.geometry())

    def msg(self, message):
        self.statusBar().showMessage(message)

def stylesheet(self):
        return """
        QTableView
        {
            border: 1px solid grey;
            border-radius: 0px;
            font-size: 8pt;
            background-color: #e8eaf3;
            selection-color: #ffffff;
        }
        QTableView::item:hover
        {   
            color: black;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #729fcf, stop:1 #d3d7cf);           
        }
        
        QTableView::item:selected 
        {
            color: #F4F4F4;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6169e1, stop:1 #3465a4);
        } 

        QStatusBar
        {
            font-size: 8pt;
            color: #57579e;
        }

        QPushButton
        {
            font-size: 8pt;
        }

        QPushButton:hover
        {   
            color: black;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #729fcf, stop:1 #d3d7cf);           
            border: 1px solid #b7b7b7 inset;
            border-radius: 3px;
        }
        QComboBox
        {
            font-size: 8pt;
        }
    """
###################################     
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    app.setApplicationName('SQLViewer')
    main = SqliteView("")
    main.show()
    if len(sys.argv) > 1:
        print(sys.argv[1])
        main.fileOpenStartup(sys.argv[1])
    sys.exit(app.exec_())
