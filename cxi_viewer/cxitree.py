#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL

class CXITree(QtGui.QTreeWidget):
    def __init__(self,parent=None):        
        QtGui.QTreeWidget.__init__(self,parent)
        self.parent = parent
        self.itemClicked.connect(self.handleClick)
        self.itemExpanded.connect(self.treeChanged)
        self.itemCollapsed.connect(self.treeChanged)
        self.resizeColumnToContents(0)
    def handleClick(self,item,column):
        if(item.text(column) == "Click to display"):
            data = self.datasets[str(item.text(2))]
            if(numpy.iscomplexobj(data[0])):
                data = numpy.abs(data)
            if(len(data.shape) == 1):
                data.form = '1D Data'
                pass
            elif(len(data.shape) == 2): 
#                self.parent.view.imshow(data)
                data.form = '2D Image'
                self.parent.view.loadImage(data)
                print str(item.text(2))
                self.parent.statusBar.showMessage("Loaded %s" % (str(item.text(2))),1000)
            elif(len(data.shape) == 3):
                # Check for the axis attribute
                if('axes' in self.datasets[str(item.text(2))].attrs.keys() is not None):
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

    def treeChanged(self):
        self.manageSizes()
    def manageSizes(self):
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        width = self.columnWidth(0) + min(125,self.columnWidth(1))
        sizes = self.parent.splitter.sizes()
        sizes[0] = width
        self.parent.splitter.setSizes(sizes)        
    def buildTree(self,filename):
        self.clear();
        self.datasets = {}
        self.setColumnCount(2)
        self.f = h5py.File(filename, "r")
        root = QtGui.QTreeWidgetItem(["/"])
        self.addTopLevelItem(root)
        item = QtGui.QTreeWidgetItem([QtCore.QFileInfo(filename).fileName()])
        item.setToolTip(0,filename)
        root.addChild(item)
        self.buildBranch(self.f,item)
        self.parent.view.clear()
        self.parent.datasetProp.clearDataset()
        self.loadData1()
    def buildBranch(self,group,item):        
            for g in group.keys():
                lst = [g]
                if(isinstance(group[g],h5py.Group)):
                    child = QtGui.QTreeWidgetItem(lst)
                    self.buildBranch(group[g],child)
                    item.addChild(child)                                    
                else:
                    if(not group[g].shape or reduce(mul,group[g].shape) < 10):
                        lst.append(str(group[g][()]))
                    else:
                        lst.append("Click to display")
                        lst.append(group[g].name)
                        self.datasets[group[g].name] = group[g]
                    item.addChild(QtGui.QTreeWidgetItem(lst))
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