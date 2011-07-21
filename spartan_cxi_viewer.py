#!/usr/bin/python
import h5py
import sys
from PyQt4 import QtGui, QtCore, Qt
import matplotlib.pyplot as plt
from operator import mul
import numpy

class Viewer(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.tree = QtGui.QTreeWidget(self)
        self.setCentralWidget(self.tree)
        self.buildTree()
        self.tree.itemClicked.connect(self.handleClick)
    def handleClick(self,item,column):
        if(item.text(column) == "Click to display"):
            if(numpy.iscomplexobj(self.datasets[str(item.text(2))])):
                plt.imshow(numpy.abs(self.datasets[str(item.text(2))]))
            else:
                plt.imshow(self.datasets[str(item.text(2))])
    def buildTree(self):
        self.datasets = {}
        self.tree.setColumnCount(2)
        self.f = h5py.File(sys.argv[1], "r")
        item = QtGui.QTreeWidgetItem(QtCore.QStringList("/"))
        self.tree.addTopLevelItem(item)
        self.buildBranch(self.f,item)
    def buildBranch(self,group,item):        
            for g in group.keys():
                lst = QtCore.QStringList(g)
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

app = QtGui.QApplication(sys.argv)
aw = Viewer()
aw.show()
sys.exit(app.exec_())
