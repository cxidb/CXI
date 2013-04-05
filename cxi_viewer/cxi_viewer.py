#!/usr/bin/env python
import h5py
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
from operator import mul
import numpy
import math
from geometry import *
from datasetprop import *
from cxitree import *
from view import *

"""
Wishes:

Infinite subplots
Color tagged images
Double click to zoom on image (double click again zoom back to width of column). Also changes to 1 column view
View only tagged ones
Tagging with numbers
Different tags different colors
Multiple tags per image

"""

        
class Viewer(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("Initializing...")
        self.splitter = QtGui.QSplitter(self)
        self.view = View(self)
        self.tree = CXITree(self)
        self.datasetProp = DatasetProp(self)
#        self.datasetProp.hide()                
        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.datasetProp)
        
        self.splitter.setStretchFactor(0,0)
        self.splitter.setStretchFactor(1,1)
        self.setCentralWidget(self.splitter)
        self.statusBar.showMessage("Initialization complete.",1000)
        self.init_menus()
        self.geometry = Geometry();
        self.resize(800,450)
        settings = QtCore.QSettings()
        if(settings.contains("geometry")):
            self.restoreGeometry(settings.value("geometry"));
        if(settings.contains("windowState")):
            self.restoreState(settings.value("windowState"));
        if(not settings.contains("scrollDirection")):
            settings.setValue("scrollDirection", 1);  
        QtCore.QTimer.singleShot(0,self.after_show)

    def after_show(self):
        if(len(sys.argv) > 1):
            self.tree.buildTree(sys.argv[1])
        
    def init_menus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"));
        self.openFile = QtGui.QAction("Open",self)
        self.fileMenu.addAction(self.openFile)
        self.openFile.triggered.connect(self.openFileClicked)
        self.preferences = QtGui.QAction("Preferences",self)
        self.fileMenu.addAction(self.preferences)
        self.preferences.triggered.connect(self.preferencesClicked)

        self.geometryMenu = self.menuBar().addMenu(self.tr("&Geometry"));
        self.assembleGeometry = QtGui.QAction("Assemble",self)
        self.geometryMenu.addAction(self.assembleGeometry)
        self.assembleGeometry.triggered.connect(self.assembleGeometryClicked)
        self.viewMenu = self.menuBar().addMenu(self.tr("&View"));

        self.viewFileTree = QtGui.QAction("File Tree",self)
        self.viewFileTree.setCheckable(True);
        self.viewFileTree.setChecked(True);
        self.viewMenu.addAction(self.viewFileTree)
        self.viewFileTree.triggered.connect(self.viewFileTreeClicked)

        self.viewDatasetProperties = QtGui.QAction("Dataset Properties",self)
        self.viewDatasetProperties.setCheckable(True);
        self.viewDatasetProperties.setChecked(True);
        self.viewMenu.addAction(self.viewDatasetProperties)
        self.viewDatasetProperties.triggered.connect(self.viewDatasetPropertiesClicked)

    def openFileClicked(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self,"Open CXI File", None, "CXI Files (*.cxi)");
        if(fileName[0]):
            self.tree.buildTree(fileName[0])
    def assembleGeometryClicked(self):
        self.geometry.assemble_detectors(self.tree.f)
    def viewFileTreeClicked(self,checked):
        if(checked):
            self.statusBar.showMessage("Showing CXI file tree",1000)
            self.tree.show()
        else:
            self.statusBar.showMessage("Hiding CXI file tree",1000)
            self.tree.hide()
    def viewDatasetPropertiesClicked(self,checked):
        if(checked):
            self.statusBar.showMessage("Showing dataset properties",1000)
            self.datasetProp.show()
        else:
            self.statusBar.showMessage("Hiding dataset properties",1000)
            self.datasetProp.hide()
    def closeEvent(self,event):
        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        QtGui.QMainWindow.closeEvent(self,event)

    def preferencesClicked(self):
        diag = PreferencesDialog(self)
        settings = QtCore.QSettings()
        if(diag.exec_()):
            if(diag.natural.isChecked()):
                settings.setValue("scrollDirection",-1)
            else:
                settings.setValue("scrollDirection",1)
   
class PreferencesDialog(QtGui.QDialog):
    def __init__(self,parent):
        QtGui.QDialog.__init__(self,parent,QtCore.Qt.WindowTitleHint)
        self.resize(300,150)

        settings = QtCore.QSettings()

        buttonBox = QtGui.QDialogButtonBox(QtCore.Qt.Horizontal)
        buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.setLayout(QtGui.QVBoxLayout());
        grid = QtGui.QGridLayout()
        grid.addWidget(QtGui.QLabel("Scroll Direction:",self),0,0)
        self.natural = QtGui.QRadioButton("Natural (Mac)")
        self.traditional = QtGui.QRadioButton("Traditional (Pc)")
        if(settings.value("scrollDirection") == -1):
            self.natural.setChecked(True)
            self.traditional.setChecked(False)
        else:
            self.natural.setChecked(False)
            self.traditional.setChecked(True)
        grid.addWidget(self.traditional,0,1);
        grid.addWidget(self.natural,1,1);
#    We'll need this when we add more options
#        f = QtGui.QFrame(self)
#        f.setFrameStyle(QtGui.QFrame.HLine | (QtGui.QFrame.Sunken))
#        grid.addWidget(f,2,0,1,2);
        self.layout().addLayout(grid)
        self.layout().addStretch()

        f = QtGui.QFrame(self)
        f.setFrameStyle(QtGui.QFrame.HLine | (QtGui.QFrame.Sunken)) 
        self.layout().addWidget(f)
        self.layout().addWidget(buttonBox)





QtCore.QCoreApplication.setOrganizationName("CXIDB");
QtCore.QCoreApplication.setOrganizationDomain("cxidb.org");
QtCore.QCoreApplication.setApplicationName("CXI Viewer");
app = QtGui.QApplication(sys.argv)
aw = Viewer()
aw.show()
ret = app.exec_()
aw.view.stopThreads()
sys.exit(ret)
