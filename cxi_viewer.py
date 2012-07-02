#!/usr/bin/python
import h5py
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
import matplotlib.pyplot as plt
from operator import mul
import numpy
import signal
import scipy.interpolate
import scipy.ndimage

signal.signal(signal.SIGINT, signal.SIG_DFL)

def onclick(event):
    z = plt.gca().get_images()[0].get_array()
    x = numpy.arange(0, z.shape[0], 1)
    y = numpy.arange(0, z.shape[1], 1)
    v = scipy.ndimage.map_coordinates(z, [[event.ydata], [event.xdata]], order=1)
    print 'xdata=%f, ydata=%f value=%e'%(
        event.xdata, event.ydata, v[0])

class CXITree(QtGui.QTreeWidget):
    def __init__(self,parent=None):        
        QtGui.QTreeWidget.__init__(self,parent)
        self.parent = parent
        self.buildTree()
        self.itemClicked.connect(self.handleClick)
        self.itemExpanded.connect(self.treeChanged)
        self.itemCollapsed.connect(self.treeChanged)
        self.resizeColumnToContents(0)
    def handleClick(self,item,column):
        if(item.text(column) == "Click to display"):
            data = self.datasets[str(item.text(2))]
            fig = plt.figure()
            ax = fig.add_axes([0, 0, 1, 1])            
            if(numpy.iscomplexobj(data)):
                data = numpy.abs(data)
            if(len(data.shape) == 1):
                plt.plot(data)
            else:
                ax.imshow(data)
                self.parent.view.imshow(data)
#                cid = fig.canvas.mpl_connect('button_press_event', onclick)
    def treeChanged(self):
        self.manageSizes()
    def manageSizes(self):
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        width = self.columnWidth(0) + min(125,self.columnWidth(1))
        sizes = self.parent.splitter.sizes()
        sizes[0] = width
        self.parent.splitter.setSizes(sizes)        
    def buildTree(self):
        self.datasets = {}
        self.setColumnCount(2)
        self.f = h5py.File(sys.argv[1], "r")
        item = QtGui.QTreeWidgetItem(QtCore.QStringList("/"))
        self.addTopLevelItem(item)
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


class View(QtOpenGL.QGLWidget):
    def __init__(self,parent=None):
        QtOpenGL.QGLWidget.__init__(self,parent)

    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if(self.width() and self.height()):
            gluOrtho2D(0.0, self.width(), 0.0, self.width());
        self.has_data = False
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();  
    def resizeGL(self, w, h):
        '''
        Resize the GL window 
        '''
        
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if(w and h):
            gluOrtho2D(0.0, w, 0.0, h);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();  
    def paintGL(self):
        '''
        Drawing routine
        '''
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glEnable(GL_TEXTURE_2D)
        if(self.has_data):
            img_width = self.data.shape[1]
            img_height = self.data.shape[0]
            glTranslatef(self.width()/2.,self.height()/2.,0)
            glScalef(4.0,4.0,1.0); 
            glTranslatef(-img_width/2.,-img_height/2.,0)
            glBindTexture (GL_TEXTURE_2D, self.texture);
            glBegin (GL_QUADS);
            glTexCoord2f (0.0, 0.0);
            glVertex3f (0, img_height, 0.0);
            glTexCoord2f (1.0, 0.0);
            glVertex3f (img_width, img_height, 0.0);
            glTexCoord2f (1.0, 1.0);
            glVertex3f (img_width, 0, 0.0);
            glTexCoord2f (0.0, 1.0);
            glVertex3f (0, 0, 0.0);
            glEnd ();
        glDisable(GL_TEXTURE_2D)
        glFlush()
    def imshow(self,data):
        self.data = data
        offset = numpy.min(data);
        scale = (numpy.max(data)-offset)/256.0
        if(scale == 0):
            scale = 1
        imageData = numpy.ones((data.shape[0],data.shape[1],3),dtype=numpy.uint8)
        imageData[:,:,0] = (data-offset)/scale
        imageData[:,:,1] = (data-offset)/scale
        imageData[:,:,2] = (data-offset)/scale
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture);
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, data.shape[1], data.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, imageData);
        self.has_data = True
        
class Viewer(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("Initializing...")
        self.splitter = QtGui.QSplitter(self)
        self.view = View(self)
        self.tree = CXITree(self)
        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.view)
        self.splitter.setStretchFactor(0,0)
        self.splitter.setStretchFactor(1,1)
        self.setCentralWidget(self.splitter)
        self.statusBar.showMessage("Initialization complete.",1000)


app = QtGui.QApplication(sys.argv)
aw = Viewer()
aw.show()
sys.exit(app.exec_())
