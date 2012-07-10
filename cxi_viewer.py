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

def sizeof_fmt(num):
    for x in ['bytes','kB','MB','GB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    return "%3.1f %s" % (num, 'TB')

class Geometry:
    def __init__(self):
        pass
    def read_detector_geometry(self,det):
        geom = numpy.eye(3,4)
        try:
            o = det["geometry_1/orientation"]
            for i in range(0,2):
                for j in range(0,3):
                    geom[i,j] = o[i*3+j]
            geom[2,0:3] = numpy.cross(geom[0,0:3],geom[1,0:3])
            print geom
        except KeyError:
            pass
        try:
            c = det["corner_position"]
            for i in range(0,3):
                geom[i,3] = c[i]
        except KeyError:
            pass
        try:
            t = det["geometry_1/translation"]
            for i in range(0,3):
                geom[i,3] = t[i]
        except KeyError:
            pass
        return geom

    def find_detectors(self,fid):
        det_id = 1;
        detectors = []
        while(True):
            try:
                path = "/entry_1/instrument_1/detector_%d" % (det_id);
                det = fid[path]
                if(len(det["data"].shape) == 2):
                    detectors.append(det)
            except KeyError:
                break
            det_id += 1
        return detectors
    def find_corners(self):
        corners = {'x':[0,0],'y':[0,0]};
        for d,g in zip(self.detectors,self.geometries):
            h = d["data"].shape[1]*d["y_pixel_size"][()]
            w = d["data"].shape[0]*d["x_pixel_size"][()]
#            print h
#            print w
            for x in range(-1,2,2):
                for y in range(-1,2,2):
                    v = numpy.matrix([[w*x/2.0],[h*y/2.0],[0],[1]])
                    c = g*v
                    if(corners['x'][0] > c[0]):
                        corners['x'][0] = c[0]
                    if(corners['x'][1] < c[0]):
                        corners['x'][1] = c[0]
                    if(corners['y'][0] > c[1]):
                        corners['y'][0] = c[1]
                    if(corners['y'][1] < c[1]):
                        corners['y'][1] = c[1]
                    print "corner ",c
        print corners
    def assemble_detectors(self,fid):
        print fid
        self.detectors = self.find_detectors(fid)
        self.geometries = []
        for d in self.detectors:
            geom = self.read_detector_geometry(d)
            self.geometries.append(geom)
        self.find_corners()

class DatasetProp(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.parent = parent
        self.vbox = QtGui.QVBoxLayout()
        self.generalBox = QtGui.QGroupBox("General Properties");
        self.generalBox.vbox = QtGui.QVBoxLayout()
        self.generalBox.setLayout(self.generalBox.vbox)        
        self.dimensionality = QtGui.QLabel("Dimensions:", parent=self)
        self.datatype = QtGui.QLabel("Data Type:", parent=self)
        self.datasize = QtGui.QLabel("Data Size:", parent=self)
        self.dataform = QtGui.QLabel("Data Form:", parent=self)
        self.generalBox.vbox.addWidget(self.dimensionality)
        self.generalBox.vbox.addWidget(self.datatype)
        self.generalBox.vbox.addWidget(self.datasize)
        self.generalBox.vbox.addWidget(self.dataform)

        self.imageStackBox = QtGui.QGroupBox("Image Stack Properties");
        self.imageStackBox.vbox = QtGui.QVBoxLayout()
        self.imageStackBox.setLayout(self.imageStackBox.vbox)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Slice:"))
        self.imageStackSlice = QtGui.QSpinBox(parent=self)
        

        self.imageStackSlice.valueChanged.connect(self.imageStackSliceChanged)                
        hbox.addWidget(self.imageStackSlice)
        self.imageStackBox.vbox.addLayout(hbox)
        self.imageStackBox.hide()
        
        self.vbox.addWidget(self.generalBox)
        self.vbox.addWidget(self.imageStackBox)
        self.vbox.addStretch()
        self.setLayout(self.vbox)
    def setDataset(self,data):
        self.data = data
        print "here"
        string = "Dimensions: "
        for d in data.shape:
            string += str(d)+"x"
        string = string[:-1]
        self.dimensionality.setText(string)
        self.datatype.setText("Data Type: %s" % (data.dtype.name))
        self.datasize.setText("Data Size: %s" % sizeof_fmt(data.dtype.itemsize*reduce(mul,data.shape)))
        self.dataform.setText("Data Form: %s" % data.form)
        if(data.form == '2D Image Stack'):
            self.imageStackSlice.setMinimum(0);
            self.imageStackSlice.setMaximum(data.shape[0]-1);
            self.imageStackSlice.setValue(0)
            self.imageStackBox.show()
        else:
            self.imageStackBox.hide()
            
    def imageStackSliceChanged(self,slice):
        self.parent.view.imshow(self.data[slice,:,:])
        self.parent.statusBar.showMessage("Loaded slice %d" % (slice),1000)

        
        
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
#            fig = plt.figure()
#            ax = fig.add_axes([0, 0, 1, 1])            
            if(numpy.iscomplexobj(data)):
                data = numpy.abs(data)
            if(len(data.shape) == 1):
                data.form = '1D Data'
                pass
#                plt.plot(data)
            elif(len(data.shape) == 2): 
#                ax.imshow(data)
                self.parent.view.imshow(data)
                data.form = '2D Image'
            elif(len(data.shape) == 3):
                msgBox = QtGui.QMessageBox();
                msgBox.setText("Display data as a 2D series of images or as a 3D volume?");
                if(data.shape[2] > (data.shape[1] + data.shape[0]) * 3 or
                   data.shape[2] < (data.shape[1] + data.shape[0]) / 3):
                    button_2D = msgBox.addButton(self.tr("2D series"), QtGui.QMessageBox.AcceptRole);
                    button_3D = msgBox.addButton(self.tr("3D volume"), QtGui.QMessageBox.RejectRole);
                else:
                    msgBox.addButton(self.tr("2D series"), QtGui.QMessageBox.RejectRole);
                    msgBox.addButton(self.tr("3D volume"), QtGui.QMessageBox.AcceptRole);
                res = msgBox.exec_();
                if(msgBox.clickedButton() == button_2D):
                    self.parent.view.imshow(data[0,:,:])
                    self.parent.statusBar.showMessage("Loaded slice 0",1000)
                    data.form = '2D Image Stack'
                elif(msgBox.clickedButton() == button_3D):
                    wrnBox = QtGui.QMessageBox();
                    wrnBox.setText("CXI Viewer currently does not support the visualization of 3D volumes.")
                    wrnBox.setInformativeText('Please use an alternative such as LLNL\'s excelent <a href="http://llnl.gov/visit">VisIt</a>.')
                    wrnBox.setIcon(QtGui.QMessageBox.Warning)
                    wrnBox.exec_();
                    return
                    data.form = '3D Image Volume'                    
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
        self.translation = [0,0]
        self.zoom = 1.0
        self.setFocusPolicy(Qt.Qt.ClickFocus)
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
            glTranslatef(self.translation[0],self.translation[1],0)
            glScalef(4.0,4.0,1.0);
            glScalef(self.zoom,self.zoom,1.0); 
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
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, data.shape[1], data.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, imageData);
        self.has_data = True
        self.updateGL()
    def wheelEvent(self, event):
        self.scaleZoom(1+(event.delta()/8.0)/360)
    def keyPressEvent(self, event):
        delta = self.width()/20
        if(event.key() == Qt.Qt.Key_Up):
            self.translation[1] -= delta
            self.updateGL()
        elif(event.key() == Qt.Qt.Key_Down):
            self.translation[1] += delta
            self.updateGL()
        elif(event.key() == Qt.Qt.Key_Left):
            self.translation[0] += delta
            self.updateGL()
        elif(event.key() == Qt.Qt.Key_Right):
            self.translation[0] -= delta
            self.updateGL()
        elif(event.key() == Qt.Qt.Key_Plus):
            self.scaleZoom(1.05)
        elif(event.key() == Qt.Qt.Key_Minus):
            self.scaleZoom(0.95)
    def mouseReleaseEvent(self, event):
        self.dragging = False

    def mousePressEvent(self, event):
        self.dragStart = event.globalPos()
        self.dragPos = event.globalPos()
        self.dragging = True
        
    def mouseMoveEvent(self, event):
        if(self.dragging):
            self.translation[0] += (event.globalPos()-self.dragPos).x()
            self.translation[1] -= (event.globalPos()-self.dragPos).y()
            self.dragPos = event.globalPos()
            self.updateGL()
    def scaleZoom(self,ratio):
        self.zoom *= ratio
        self.translation[0] *= ratio
        self.translation[1] *= ratio           
        self.updateGL()

            
        
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
    def init_menus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"));
        self.openFile = QtGui.QAction("Open",self)
        self.fileMenu.addAction(self.openFile)
        self.openFile.triggered.connect(self.openFileClicked)
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
        print "here"
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

app = QtGui.QApplication(sys.argv)
aw = Viewer()
aw.show()
sys.exit(app.exec_())
