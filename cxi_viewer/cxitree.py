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

class DatasetButton(QtGui.QPushButton):
    needDataset = QtCore.Signal(str)    
    def __init__(self,imageFile,datasetMode,menu=None):
        QtGui.QPushButton.__init__(self)
        self.datasetMode = datasetMode
        self.setName()
        self.setIcon(QtGui.QIcon(imageFile))
        S = 30
        Htot = S + 15
        Wtot = 400
        self.setIconSize(QtCore.QSize(S,S))
        self.setToolTip("drag dataset here")
        self.setAcceptDrops(True)
        self.setFixedSize(QtCore.QSize(Wtot,Htot))
        if menu != None:
            self.setMenu(menu)
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('text/plain'):
            e.accept()
        else:
            e.ignore() 
    def dropEvent(self, e):
        t = e.mimeData().text()
        self.needDataset.emit(t)
    def setName(self,name=None):
        if name == None:
            self.setStyleSheet("text-align: left; font-style: italic")
            self.setText("drag %s dataset here" % self.datasetMode)
        else:
            self.setStyleSheet("text-align: left; font-style: roman") 
            self.setText(name)

class DatasetBox(QtGui.QHBoxLayout):
    def __init__(self,imageFile,datasetMode,menu=None):
        QtGui.QHBoxLayout.__init__(self)
        self.button = DatasetButton(imageFile,datasetMode,menu)
        self.addWidget(self.button)
        self.vbox = QtGui.QVBoxLayout()
        self.addLayout(self.vbox)

class MaskMenu(QtGui.QMenu):
    def __init__(self,parent=None):
        QtGui.QMenu.__init__(self,parent)
        self.PIXELMASK_BITS = {'perfect' : 0,# PIXEL_IS_PERFECT
                               'invalid' : 1,# PIXEL_IS_INVALID
                               'saturated' : 2,# PIXEL_IS_SATURATED
                               'hot' : 4,# PIXEL_IS_HOT
                               'dead' : 8,# PIXEL_IS_DEAD
                               'shadowed' : 16, # PIXEL_IS_SHADOWED
                               'peakmask' : 32, # PIXEL_IS_IN_PEAKMASK
                               'ignore' : 64, # PIXEL_IS_TO_BE_IGNORED
                               'bad' : 128, # PIXEL_IS_BAD
                               'resolution' : 256, # PIXEL_IS_OUT_OF_RESOLUTION_LIMITS
                               'missing' : 512, # PIXEL_IS_MISSING
                               'halo' : 1024} # PIXEL_IS_IN_HALO
        self.maskActions = {}
        for key in self.PIXELMASK_BITS.keys():
            self.maskActions[key] = self.addAction(key)
            self.maskActions[key].setCheckable(True)
            self.maskActions[key].setChecked(True)
    def getMaskOutBits(self):
        maskOutBits=0
        for key in self.maskActions:
            if self.maskActions[key].isChecked():
                maskOutBits |= self.PIXELMASK_BITS[key]
        return maskOutBits


class CXINavigation(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.parent = parent
        self.vbox = QtGui.QVBoxLayout()
        self.setLayout(self.vbox)

        self.CXITree = CXITree(self)
        self.vbox.addWidget(self.CXITree)

        self.datasetBoxes = {}

        self.datasetBoxes["image"] = DatasetBox("./icons/image.png","image")
        self.vbox.addLayout(self.datasetBoxes["image"])

        self.maskMenu = MaskMenu(self)
        self.datasetBoxes["mask"] = DatasetBox("./icons/mask_simple.png","mask",self.maskMenu)
        self.vbox.addLayout(self.datasetBoxes["mask"])

        self.datasetBoxes["sorting"] = DatasetBox("./icons/sort.png","sorting")
        self.vbox.addLayout(self.datasetBoxes["sorting"])

        self.datasetBoxes["plot"] = DatasetBox("./icons/plot.png","plot")
        self.vbox.addLayout(self.datasetBoxes["plot"])

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('text/plain'):
            e.accept()
        else:
            e.ignore() 
    def dropEvent(self, e):
        t = e.mimeData().text()
        self.clear()
        self.setText(t)
        self.needDataset.emit(t)



class CXITree(QtGui.QTreeWidget):
    datasetClicked = QtCore.Signal(str)    
    def __init__(self,parent=None):        
        QtGui.QTreeWidget.__init__(self,parent)
        self.parent = parent
        self.itemExpanded.connect(self.treeChanged)
        self.itemCollapsed.connect(self.treeChanged)
        #self.setHeaderLabels(["CXI-file tree"])
        self.resizeColumnToContents(0)
        self.itemClicked.connect(self.handleClick)
        self.setDragEnabled(True)
        self.header().close()
    def treeChanged(self):
        self.manageSizes()
    def manageSizes(self):
        self.resizeColumnToContents(0)
    def buildTree(self,filename):
        self.clear();
        self.datasets = {}
        self.setColumnCount(1)
        self.f = h5py.File(filename, "r")
        self.root = QtGui.QTreeWidgetItem(["/"])
        self.addTopLevelItem(self.root)
        item = QtGui.QTreeWidgetItem([QtCore.QFileInfo(filename).fileName()])
        item.setToolTip(0,filename)
        self.root.setExpanded(True)
        self.root.addChild(item)
        self.buildBranch(self.f,item)
        self.loadData1(item)
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
                    S = 70
                    # text or 0D
                    if numDims == 0 or dataset.isCXIText():
                        R = 255-S
                        G = 255-S
                        B = 255-S
                    # 1D
                    elif numDims == 1:
                        R = 255-S
                        G = 255-S
                        B = 255
                    # 2D red
                    elif numDims == 2:
                        R = 255-S
                        G = 255
                        B = 255-S 
                    # 3D blue
                    elif numDims == 3:
                        R = 255
                        G = 255-S
                        B = 255-S
                    # datsets which are not stacks lighter
                    if not dataset.isCXIStack():
                        fade = S
                        R -= fade
                        G -= fade
                        B -= fade
                    child.setForeground(0,QtGui.QBrush(QtGui.QColor(R,G,B)))
                    # make bold if it is a dataset called 'data'
                    if g.rsplit("/",1)[-1] == 'data':
                        font = QtGui.QFont()
                        font.setBold(True)
                        child.setFont(0,font)
                item.addChild(child)
    def loadData1(self,item):
        root = item
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
    def startDrag(self, event):
        # create mime data object
        mime = QtCore.QMimeData()
        mime.setText(self.currentItem().text(self.columnPath))
        # start drag 
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.start(QtCore.Qt.MoveAction)
    def handleClick(self,item,column):
        if(item.text(self.columnPath) in self.datasets.keys()):
            self.datasetClicked.emit(item.text(self.columnPath))

