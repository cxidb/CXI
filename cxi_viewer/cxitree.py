#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
import h5py
from operator import mul
import numpy

class CXINavigation(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.vbox = QtGui.QVBoxLayout()
        self.setLayout(self.vbox)

        self.CXINavigationTop = QtGui.QGroupBox("View")
        self.CXINavigationTop.vbox = QtGui.QVBoxLayout()
        self.CXINavigationTop.setLayout(self.CXINavigationTop.vbox)        
        self.CXITreeTop = CXITreeTop(self)
        self.CXINavigationTop.vbox.addWidget(self.CXITreeTop)
        self.vbox.addWidget(self.CXINavigationTop)

        self.CXINavigationBottom = QtGui.QGroupBox("Sort")
        self.CXINavigationBottom.vbox = QtGui.QVBoxLayout()
        self.CXINavigationBottom.setLayout(self.CXINavigationBottom.vbox)
        self.CXITreeBottom = CXITreeBottom(self)
        self.CXINavigationBottom.vbox.addWidget(self.CXITreeBottom)
        self.vbox.addWidget(self.CXINavigationBottom)


class CXITree(QtGui.QTreeWidget):
    def __init__(self,parent=None):        
        QtGui.QTreeWidget.__init__(self,parent)
        self.parent = parent
        self.itemExpanded.connect(self.treeChanged)
        self.itemCollapsed.connect(self.treeChanged)
        self.setHeaderLabels(["CXI-file tree"])
        self.resizeColumnToContents(0)
        self.currDatasetName = self.currGroupName = None
    def treeChanged(self):
        self.manageSizes()
    def manageSizes(self):
        self.resizeColumnToContents(0)
    def buildTree(self,filename):
        self.clear();
        self.datasets = {}
        self.setColumnCount(1)
        self.f = h5py.File(filename, "r")
        root = QtGui.QTreeWidgetItem(["/"])
        self.addTopLevelItem(root)
        item = QtGui.QTreeWidgetItem([QtCore.QFileInfo(filename).fileName()])
        item.setToolTip(0,filename)
        root.addChild(item)
        self.buildBranch(self.f,item)
        #self.loadData1()
    def buildBranch(self,group,item):
        self.columnPath = 1
        for g in group.keys():
            lst = [g]
            if(isinstance(group[g],h5py.Group)):
                child = QtGui.QTreeWidgetItem(lst)
                self.buildBranch(group[g],child)
                item.addChild(child)
            else:
                if(not group[g].shape or reduce(mul,group[g].shape) < 10):
                    lst.append(str(group[g][()]))
                    lst.append("")
                    child = QtGui.QTreeWidgetItem(lst)
                else:
                    dataset = group[g]
                    ds_dtype = dataset.dtype.name
                    ds_shape = dataset.shape
                    self.datasets[group[g].name] = dataset
                    string = "<i>"+ds_dtype+"</i> ("
                    for d in ds_shape:
                        string += str(d)+","
                    string = string[:-3]
                    string += ")"
                    lst.append(group[g].name)
                    child = QtGui.QTreeWidgetItem(lst)
                    child.setToolTip(self.columnPath-1,string)
                    if len(ds_shape) == 1:
                        R = 0
                        G = 0
                        B = 120
                    if len(ds_shape) == 2: 
                        R = 0
                        G = 120
                        B = 0
                    if len(ds_shape) == 3:
                        R = 120
                        G = 0
                        B = 0
                    child.setForeground(0,QtGui.QBrush(QtGui.QColor(R,G,B)))
                    if g.rsplit("/",1)[-1] == 'data':
                        font = QtGui.QFont()
                        font.setBold(True)
                        child.setFont(0,font)
                item.addChild(child)

class CXITreeTop(CXITree):
    def __init__(self,parent=None):        
        CXITree.__init__(self,parent)
        self.itemClicked.connect(self.handleClick)
    def handleClick(self,item,column):
        if(item.text(self.columnPath) != ""):
            self.currDatasetName = str(item.text(self.columnPath))
            self.currGroupName = str(item.text(self.columnPath).rsplit("/",1)[0])
            data = self.datasets[self.currDatasetName]
            if(numpy.iscomplexobj(data[0])):
                data = numpy.abs(data)
            if(len(data.shape) == 1):
                data.form = '1D Data'
                pass
            elif(len(data.shape) == 2): 
#                self.parent.view.imshow(data)
                data.form = '2D Image'
                self.parent.datasetProp.clear()
                self.parent.view.clear()
                self.parent.view.loadImage(data)
                print str(item.text(2))
                self.parent.statusBar.showMessage("Loaded %s" % (str(item.text(self.columnPath))),1000)
            elif(len(data.shape) == 3):
                # Check for the axis attribute
                if('axes' in self.datasets[str(item.text(self.columnPath))].attrs.keys() is not None):
                    self.parent.datasetProp.clear()
                    self.parent.view.clear()
                    self.parent.view.loadStack(data)
                    self.parent.statusBar.showMessage("Loaded slice 0",1000)
                    data.form = '2D Image Stack'
                else:
                    wrnBox = QtGui.QMessageBox();
                    wrnBox.setText("CXI Viewer currently does not support the visualization of 3D volumes.")
                    wrnBox.setInformativeText('Please use an alternative such as LLNL\'s excelent <a href="http://llnl.gov/visit">VisIt</a>.')
                    wrnBox.setIcon(QtGui.QMessageBox.Warning)
                    wrnBox.exec_();
                    return 
            else:
                QtGui.QMessageBox.warning(self,self.tr("CXI Viewer"),self.tr("Cannot display datasets with more than 3 dimensions. The selected dataset has %d dimensions." %(len(data.shape))))
                return
            self.parent.datasetProp.setDataset(data);
    def loadData1(self):
        root = self.topLevelItem(0)
        root.setExpanded(True)
        path = ("entry_1","data_1","data")
        for section in path:
            found = False
            for i in range(0,root.childCount()):
                child = root.child(i)
                if(child.text(0) == section):
                    child.setExpanded(True)
                    root = child
                    found = True
                    break
            if(not found):
                break
        if(found):
            self.handleClick(root,1)
            return 1
        return 0

class CXITreeBottom(CXITree):
    def __init__(self,parent=None):        
        CXITree.__init__(self,parent)
        self.itemClicked.connect(self.handleClick)
    def handleClick(self,item,column):
        if(item.text(self.columnPath) != ""):
            self.currDatasetName = str(item.text(self.columnPath))
            self.currGroupName = str(item.text(self.columnPath).rsplit("/",1)[0])
            data = self.datasets[self.currDatasetName]
            if(len(data.shape) == 1):
                data.form = '1D Data'
                self.currentDataset = data
            else:
                QtGui.QMessageBox.warning(self,self.tr("CXI Viewer"),self.tr("Cannot sort with a dataset that has more than one dimension. The selected dataset has %d dimensions." %(len(data.shape))))
                self.currentDataset = None
            self.parent.view.loaderThread.setSortingIndices(self.currentDataset)
            self.parent.view.clearTextures()
            self.parent.view.updateGL()    
