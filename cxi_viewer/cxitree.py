#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
import h5py
from operator import mul
import numpy

# Add new functions to h5py.Dataset, names for functions are supposed to be unique in order to avoid conflicts
def isCXIStack(dataset):
    items = dataset.attrs.items()
    if len(items) > 0:
        return ("axes" == items[0][0])
    else:
        return False
h5py.Dataset.isCXIStack = isCXIStack 
def getCXIFormat(dataset):
    N = len(dataset.shape)
    if dataset.isCXIStack():
        N -= 1
    return N
h5py.Dataset.getCXIFormat = getCXIFormat
def isCXIText(dataset):
    return (dataset.dtype.name[-6:] == "string")
h5py.Dataset.isCXIText = isCXIText
def getCXIMasks(dataset):
    masks = {}
    suppMaskTypes = ["mask_shared","mask"]
    for maskType in suppMaskTypes:
        if maskType in dataset.parent.keys():
            masks[maskType] = dataset.parent[maskType]
    return masks
h5py.Dataset.getCXIMasks = getCXIMasks
def getCXIWidth(dataset):
    if dataset.isCXIStack():
        return dataset.shape[2]
    else:
        return dataset.shape[1]
h5py.Dataset.getCXIWidth = getCXIWidth
def getCXIHeight(dataset):
    if dataset.isCXIStack():
        return dataset.shape[1]
    else:
        return dataset.shape[0]
h5py.Dataset.getCXIHeight = getCXIHeight

class CXINavigation(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.parent = parent
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

        self.viewDatasetChanged = self.CXITreeTop.datasetChanged
        self.sortDatasetChanged = self.CXITreeBottom.datasetChanged


class CXITree(QtGui.QTreeWidget):
    def __init__(self,parent=None):        
        QtGui.QTreeWidget.__init__(self,parent)
        self.parent = parent
        self.itemExpanded.connect(self.treeChanged)
        self.itemCollapsed.connect(self.treeChanged)
        self.setHeaderLabels(["CXI-file tree"])
        self.resizeColumnToContents(0)
        self.currDatasetName = None
        self.itemClicked.connect(self.handleClick)
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
        self.stackSize = self.f['/entry_1/data_1/data'].shape[0]
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
                if(not group[g].shape):# or reduce(mul,group[g].shape) < 10):
                    lst.append(str(group[g][()]))
                    lst.append("")
                    child = QtGui.QTreeWidgetItem(lst)
                else:
                    dataset = self.datasets[group[g].name] = group[g]
                    ds_dtype = dataset.dtype.name
                    ds_shape = dataset.shape
                    string = "<i>"+ds_dtype+"</i> ("
                    for d in ds_shape:
                        string += str(d)+","
                    string = string[:-1]
                    string += ")"
                    lst.append(group[g].name)
                    child = QtGui.QTreeWidgetItem(lst)
                    child.setToolTip(self.columnPath-1,string)
                    numDims = dataset.getCXIFormat()
                    # text or 0D gray
                    if numDims == 0 or dataset.isCXIText():
                        R = 100
                        G = 100
                        B = 100
                    # 1D green
                    elif numDims == 1:
                        R = 0
                        G = 100
                        B = 0
                    # 2D blue
                    elif numDims == 2:
                        R = 0
                        G = 0
                        B = 100
                    # 3D red
                    elif numDims == 3:
                        R = 100
                        G = 0
                        B = 0
                    # datsets which are not stacks lighter
                    if not dataset.isCXIStack():
                        fade = 50
                        R += fade
                        G += fade
                        B += fade
                    child.setForeground(0,QtGui.QBrush(QtGui.QColor(R,G,B)))
                    # make bold if it is a dataset called 'data'
                    if g.rsplit("/",1)[-1] == 'data':
                        font = QtGui.QFont()
                        font.setBold(True)
                        child.setFont(0,font)
                item.addChild(child)
            
    


class CXITreeTop(CXITree):
    datasetChanged = QtCore.Signal(h5py.Dataset)
    def __init__(self,parent=None):        
        CXITree.__init__(self,parent)
        self.itemClicked.connect(self.handleClick)
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
    def handleClick(self,item,column):
        if(item.text(self.columnPath) in self.datasets.keys()):
            self.currDataset = self.datasets[item.text(self.columnPath)]
            self.datasetChanged.emit(self.currDataset)


class CXITreeBottom(CXITree):
    datasetChanged = QtCore.Signal(h5py.Dataset)
    def __init__(self,parent=None):        
        CXITree.__init__(self,parent)
        self.itemClicked.connect(self.handleClick)
    def handleClick(self,item,column):
        if(item.text(self.columnPath) in self.datasets.keys()):
            self.currDataset = self.datasets[item.text(self.columnPath)]
            self.datasetChanged.emit(self.currDataset)

