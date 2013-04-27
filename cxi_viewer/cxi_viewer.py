#!/usr/bin/env python

import sys
from OpenGL.GL import *
from OpenGL.GLU import *
#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL

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
        self.view = View2D(self)
        self.datasetProp = DatasetProp(self)
        self.CXINavigation = CXINavigation(self)
        self.splitter.addWidget(self.CXINavigation)
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

        self.CXINavigation.CXITreeTop.datasetChanged.connect(self.handleViewDatasetChanged)
        self.CXINavigation.CXITreeBottom.datasetChanged.connect(self.handleSortDatasetChanged)
        self.datasetProp.maskChanged.connect(self.handleMaskChanged)
        self.datasetProp.normChanged.connect(self.handleNormChanged)
        self.datasetProp.colormapChanged.connect(self.handleColormapChanged)
        self.datasetProp.imageStackSubplotsChanged.connect(self.handleImageStackSubplotsChanged)

    def after_show(self):
        if(len(sys.argv) > 1):
            self.CXINavigation.CXITreeTop.buildTree(sys.argv[1])
            self.CXINavigation.CXITreeBottom.buildTree(sys.argv[1])
        
    def init_menus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"));
        self.openFile = QtGui.QAction("Open",self)
        self.fileMenu.addAction(self.openFile)
        self.openFile.triggered.connect(self.openFileClicked)
        self.preferences = QtGui.QAction("Preferences",self)
        self.fileMenu.addAction(self.preferences)
        self.preferences.triggered.connect(self.preferencesClicked)

        #self.geometryMenu = self.menuBar().addMenu(self.tr("&Geometry"));
        #self.assembleGeometry = QtGui.QAction("Assemble",self)
        #self.geometryMenu.addAction(self.assembleGeometry)
        #self.assembleGeometry.triggered.connect(self.assembleGeometryClicked)
        
        self.viewMenu = self.menuBar().addMenu(self.tr("&View"));

        self.viewActions = {"File Trees" : QtGui.QAction("File Trees",self),
                            "Dataset Properties" : QtGui.QAction("Dataset Properties",self),
                            "General Properties" : QtGui.QAction("General Properties",self),
                            "Display Properties" : QtGui.QAction("Display Properties",self),
                            "Mask Out Pixels" : QtGui.QAction("Mask Out Pixels",self)}

        viewNames = ["File Trees",
                     "Dataset Properties",
                     "General Properties",
                     "Display Properties",
                     "Mask Out Pixels"]
        
        for viewName in viewNames:
            act = self.viewActions[viewName]
            act.setCheckable(True)
            act.setChecked(True)
            self.viewMenu.addAction(act)
            act.triggered.connect(self.viewClicked)
            if viewName == "Dataset Properties": 
                self.viewMenu.addSeparator()

    def openFileClicked(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self,"Open CXI File", None, "CXI Files (*.cxi)");
        if(fileName[0]):
            self.CXINavigation.CXITreeTop.buildTree(fileName[0])
    def assembleGeometryClicked(self):
        self.geometry.assemble_detectors(self.CXINavigation.CXITreeTop.f)
    def viewClicked(self):
        viewBoxes = {"File Trees" : self.CXINavigation,
                     "Dataset Properties" : self.datasetProp,
                     "General Properties" : self.datasetProp.generalBox,
                     "Display Properties" : self.datasetProp.displayBox,
                     "Mask Out Pixels" : self.datasetProp.maskBox}
        viewName = self.sender().text()
        box = viewBoxes[viewName]
        checked = self.viewActions[viewName].isChecked()
        if(checked):
            self.statusBar.showMessage("Showing %s" % viewName,1000)
            box.show()
        else:
            self.statusBar.showMessage("Hiding %s" % viewName,1000)
            box.hide()
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
    def handleViewDatasetChanged(self,dataset):
        format = dataset.getCXIFormat()
        if format == 1:
            if not isinstance(self.view,View1D):
                self.view.clear()
                self.view = View1D(self)
            self.view.loadData(dataset)
        elif format == 2:
            if not isinstance(self.view,View2D):
                self.view.clear()
                self.view = View2D(self)
            self.datasetProp.clear()
            self.view.clear()
            if dataset.isCXIStack():
                self.view.loadStack(dataset)
            else:
                self.view.loadImage(dataset)
            self.statusBar.showMessage("Loaded %s" % dataset.name,1000)
        elif format == 3:
            QtGui.QMessageBox.warning(self,self.tr("CXI Viewer"),self.tr("Cannot display datasets of given shape. The selected dataset has %d dimensions." %(len(dataset.shape))))
            return
        self.datasetProp.setDataset(dataset)
    def handleSortDatasetChanged(self,dataset):
        format = dataset.getCXIFormat()
        if(format == 1):
            self.view.setSortingIndices(dataset)
            self.view.clearTextures()
            self.view.updateGL()
        else:
            QtGui.QMessageBox.warning(self,self.tr("CXI Viewer"),self.tr("Cannot sort with a dataset that has more than one dimension. The selected dataset has %d dimensions." %(len(dataset.shape))))
    def handleMaskChanged(self,mask,maskOutBits):
        self.view.setMask(mask,maskOutBits)
        self.view.clearTextures()
        self.view.updateGL()
    def handleNormChanged(self,scaling,vmin,vmax,gamma):
        self.view.loaderThread.setNorm(scaling,vmin,vmax,gamma)
        self.view.clearTextures()
        self.view.updateGL()
    def handleColormapChanged(self,colormap):
        self.view.loaderThread.setColormap(colormap)
        self.view.clearTextures()
        self.view.updateGL()
    def handleImageStackSubplotsChanged(self,plots):
        self.view.setStackWidth(plots) 

        

   
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
