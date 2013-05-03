#!/usr/bin/env python

import sys,os
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
        self.view = ViewSplitter(self)
        self.init_menus()
        self.datasetProp = DatasetProp(self)
        self.CXINavigation = CXINavigation(self)
        self.splitter.addWidget(self.CXINavigation)
        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.datasetProp)

        self.splitter.setStretchFactor(0,0)
        self.splitter.setStretchFactor(1,1)
        self.splitter.setStretchFactor(2,0)
        self.setCentralWidget(self.splitter)
        self.statusBar.showMessage("Initialization complete.",1000)
        
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
        
        self.CXINavigation.CXITree.datasetClicked.connect(self.handleDatasetClicked)
        self.view.view1D.needDataset.connect(self.handleNeedDatasetPlot)
        self.view.view1D.datasetChanged.connect(self.handleDatasetChanged)
        self.view.view2D.needDataset.connect(self.handleNeedDatasetImage)
        self.view.view2D.datasetChanged.connect(self.handleDatasetChanged)
        self.CXINavigation.datasetBoxes["image"].button.needDataset.connect(self.handleNeedDatasetImage)
        self.CXINavigation.datasetBoxes["mask"].button.needDataset.connect(self.handleNeedDatasetMask)
        self.CXINavigation.maskMenu.triggered.connect(self.handleMaskOutBitsChanged)
        self.CXINavigation.datasetBoxes["sort"].button.needDataset.connect(self.handleNeedDatasetSorting)
        self.CXINavigation.datasetBoxes["plot"].button.needDataset.connect(self.handleNeedDatasetPlot)
        self.CXINavigation.plotMenu.triggered.connect(self.handlePlotModeTriggered)
        self.datasetProp.displayPropChanged.connect(self.handleDisplayPropChanged)
        self.view.view2D.imageSelected.connect(self.datasetProp.onImageSelected)

        self.datasetProp.emitDisplayProp()

        self.setStyle()
        

    def after_show(self):
        if(len(sys.argv) > 1):
            self.openCXIFile(sys.argv[1])
    def openCXIFile(self,filename):
        self.CXINavigation.CXITree.buildTree(filename)
        self.handleNeedDatasetImage("/entry_1/data_1/data")
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

        self.CXIStyleAction = QtGui.QAction("CXI Style",self)
        self.CXIStyleAction.setCheckable(True)
        self.CXIStyleAction.setChecked(False)
        self.CXIStyleAction.triggered.connect(self.setCXIStyle)
        self.viewMenu.addAction(self.CXIStyleAction)

        self.viewMenu.addSeparator()

        act = QtGui.QAction("Full Screen",self)
        act.setShortcut(QtGui.QKeySequence("Ctrl+F"))
        act.setCheckable(True)

        act.triggered.connect(self.toggleFullScreen)
        self.viewMenu.addAction(act)

        act = QtGui.QAction("Slide Show",self)
        act.setCheckable(True)
        act.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        act.triggered.connect(self.view.view2D.toggleSlideShow)
        self.viewMenu.addAction(act)

        self.viewMenu.addSeparator()

        self.viewActions = {"File Tree" : QtGui.QAction("File Tree",self),
                            "View 1D" : QtGui.QAction("View 1D",self),
                            "View 2D" : QtGui.QAction("View 2D",self),
                            "Display Properties" : QtGui.QAction("Display Properties",self)}

        viewShortcuts = {"File Tree" : "Ctrl+T",
                         "View 1D" : "Ctrl+1",
                         "View 2D" : "Ctrl+2",
                         "Display Properties" : "Ctrl+D"}

        viewNames = ["File Tree", "Display Properties","View 1D","View 2D"]
      
        actions = {}
        for viewName in viewNames:
            actions[viewName] = self.viewActions[viewName]
            actions[viewName].setCheckable(True)
            actions[viewName].setShortcut(QtGui.QKeySequence(viewShortcuts[viewName]))
            actions[viewName].triggered.connect(self.viewClicked)
            if viewName in ["View 1D"]:
                actions[viewName].setChecked(False)
            else:
                actions[viewName].setChecked(True)
            self.viewMenu.addAction(actions[viewName])
        
        self.viewMenu.addSeparator()

        icon_width = 64
        icon_height = 64
        colormapIcons = paintColormapIcons(icon_width,icon_height)

        self.colormapMenu = QtGui.QMenu("Colormap",self)
        self.colormapActionGroup = QtGui.QActionGroup(self)

        traditionalColormaps = ['jet','hot','gray','coolwarm','gnuplot','gist_earth']
        self.colormapActions = {}
        for colormap in traditionalColormaps:            
            a = self.colormapMenu.addAction(colormapIcons.pop(colormap),colormap)
            a.setActionGroup(self.colormapActionGroup)
            a.setCheckable(True)
            self.colormapActions[colormap] = a

        self.exoticColormapMenu = QtGui.QMenu("Exotic",self)
        for colormap in colormapIcons.keys():
            a = self.exoticColormapMenu.addAction(colormapIcons[colormap],colormap)
            a.setActionGroup(self.colormapActionGroup)
            a.setCheckable(True)
            self.colormapActions[colormap] = a

        settings = QtCore.QSettings()
        if(settings.contains("colormap")):
            self.colormapActions[settings.value('colormap')].setChecked(True)
        else:
            self.colormapActions['jet'].setChecked(True)
        self.colormapMenu.addMenu(self.exoticColormapMenu)
        self.viewMenu.addMenu(self.colormapMenu)

    def openFileClicked(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self,"Open CXI File", None, "CXI Files (*.cxi)");
        if(fileName[0]):
            self.openCXIFile(fileName[0])
    def setStyle(self,fn="default.stylesheet"):
        styleFile=os.path.join(os.path.split(__file__)[0],fn)
        with open(styleFile,"r") as fh:
            self.setStyleSheet(fh.read())
    def setCXIStyle(self):
        if self.CXIStyleAction.isChecked():
            self.setStyle("dark.stylesheet")
        else:
            self.setStyle()
            #self.setStyle("")
    def assembleGeometryClicked(self):
        self.geometry.assemble_detectors(self.CXINavigation.CXITreeTop.f)
    def viewClicked(self):
        viewName = self.sender().text()
        checked = self.viewActions[viewName].isChecked()
        viewBoxes = {"File Tree" : self.CXINavigation,
                     "Display Properties" : self.datasetProp,
                     "View 1D" : self.view.view1D,
                     "View 2D" : self.view.view2D}
        box = viewBoxes[viewName]
        if(checked):
            self.statusBar.showMessage("Showing %s" % viewName,1000)
            box.show()
        else:
            self.statusBar.showMessage("Hiding %s" % viewName,1000)
            box.hide()
    def toggleFullScreen(self):
        if self.windowState() & QtCore.Qt.WindowFullScreen:
            self.showNormal()
        else:
            self.showFullScreen()
    def closeEvent(self,event):
        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("colormap", self.datasetProp.currDisplayProp['colormapText'])        
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
            self.view.setCurrentWidget(self.view.view1D)
            self.view.view1D.loadData(dataset)
        elif format == 2:
            self.view.setCurrentWidget(self.view.view2D)
            self.datasetProp.clear()
            self.view.view2D.clear()
            if dataset.isCXIStack():
                self.view.view2D.loadStack(dataset)
            else:
                self.view.view2D.loadImage(dataset)
            self.statusBar.showMessage("Loaded %s" % dataset.name,1000)
        elif format == 3:
            QtGui.QMessageBox.warning(self,self.tr("CXI Viewer"),self.tr("Cannot display datasets of given shape. The selected dataset has %d dimensions." %(len(dataset.shape))))
            return
        self.datasetProp.setDataset(dataset)
    def handleNeedDatasetImage(self,datasetName):
        dataset = self.CXINavigation.CXITree.datasets[datasetName]
        format = dataset.getCXIFormat()
        if format == 2:        
            #self.view.setCurrentWidget(self.view.view2D)
            self.CXINavigation.datasetBoxes["image"].button.setName(datasetName)
            self.datasetProp.clear()
            self.view.view2D.clear()
            if dataset.isCXIStack():
                self.view.view2D.loadStack(dataset)
                self.statusBar.showMessage("Loaded image stack: %s" % dataset.name,1000)
            else:
                self.view.view2D.loadImage(dataset)
                self.statusBar.showMessage("Loaded image: %s" % dataset.name,1000)
        else:
            QtGui.QMessageBox.warning(self,self.tr("CXI Viewer"),self.tr("Cannot sort with a dataset that has more than one dimension. The selected dataset has %d dimensions." %(len(dataset.shape))))
        self.datasetProp.setDataset(dataset)
        group = datasetName.rsplit("/",1)[0]
        if self.CXINavigation.datasetBoxes["mask"].button.text().rsplit("/",1)[0] != group:
            if group+"/mask" in self.CXINavigation.CXITree.datasets.keys():
                self.handleNeedDatasetMask(group+"/mask")
            elif group+"/mask_shared" in self.CXINavigation.CXITree.datasets.keys():
                self.handleNeedDatasetMask(group+"/mask_shared")
    def handleNeedDatasetMask(self,datasetName):
        dataset = self.CXINavigation.CXITree.datasets[datasetName]
        maskOutBits = self.CXINavigation.maskMenu.getMaskOutBits()
        self.view.view2D.setMask(dataset,maskOutBits)
        self.view.view2D.clearTextures()
        self.view.view2D.updateGL()
        self.CXINavigation.datasetBoxes["mask"].button.setName(datasetName)
        self.statusBar.showMessage("Loaded mask: %s" % dataset.name,1000)
    def handleMaskOutBitsChanged(self,action):
        self.view.view2D.setMaskOutBits(self.CXINavigation.maskMenu.getMaskOutBits())
    def handleNeedDatasetSorting(self,datasetName):
        dataset = self.CXINavigation.CXITree.datasets[datasetName]
        if dataset.getCXIFormat() == 0:
            self.view.view2D.indexProjector.setSortingArray(dataset)
            self.CXINavigation.datasetBoxes["sort"].button.setName(datasetName)
            self.statusBar.showMessage("Loaded sorting dataset: %s" % dataset.name,1000)
            self.view.view2D.updateGL()
    def handleNeedDatasetPlot(self,datasetName):
        dataset = self.CXINavigation.CXITree.datasets[datasetName]
        plotMode = self.CXINavigation.plotMenu.getPlotMode()
        self.view.view1D.show()
        self.view.view1D.loadData(dataset,plotMode)
        self.CXINavigation.datasetBoxes["plot"].button.setName(datasetName)
        self.statusBar.showMessage("Loaded plot: %s" % dataset.name,1000)
        self.viewActions["View 1D"].setChecked(True)
    def handlePlotModeTriggered(self,foovalue=None):
        datasetName = self.CXINavigation.datasetBoxes["plot"].button.text()
        if datasetName in self.CXINavigation.CXITree.datasets.keys():
            self.handleNeedDatasetPlot(datasetName)
    def handleDisplayPropChanged(self,prop):
        self.view.view2D.refreshDisplayProp(prop)
    def handleDatasetClicked(self,datasetName):
        dataset = self.CXINavigation.CXITree.datasets[datasetName]
        format = dataset.getCXIFormat()
        if format == 1:
            self.handleNeedDatasetPlot(datasetName)
        elif format == 2:
            if datasetName[:4] == "mask":
                self.handleNeedDatasetMask(datasetName)
            else:
                self.handleNeedDatasetImage(datasetName)            
    def handleDatasetChanged(self,dataset,datasetMode):
        if dataset != None:
            n = dataset.name
        else:
            n = None
        self.CXINavigation.datasetBoxes[datasetMode].button.setName(n)

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
aw.view.view2D.stopThreads()
sys.exit(ret)
