#!/usr/bin/python
import h5py
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from operator import mul
import numpy

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
        hbox.addWidget(QtGui.QLabel("Image:"))
        self.imageStackSlice = QtGui.QSpinBox(parent=self)
        self.imageStackSlice.valueChanged.connect(self.imageStackSliceChanged)                
        hbox.addWidget(self.imageStackSlice)
        self.imageStackBox.vbox.addLayout(hbox)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Step Size:"))
        self.imageStackSliceStep = QtGui.QSpinBox(parent=self)
        self.imageStackSliceStep.setMinimum(1)
        self.imageStackSliceStep.valueChanged.connect(self.imageStackSlice.setSingleStep)
        hbox.addWidget(self.imageStackSliceStep)
        self.imageStackBox.vbox.addLayout(hbox)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Subplots:"))
        self.imageStackSubplots = QtGui.QSpinBox(parent=self)
        self.imageStackSubplots.setMinimum(1)
#        self.imageStackSubplots.setMaximum(5)
        self.imageStackSubplots.valueChanged.connect(self.imageStackSubplotsChanged)                
        hbox.addWidget(self.imageStackSubplots)
        self.imageStackBox.vbox.addLayout(hbox)

        self.imageStackGlobalScale = QtGui.QCheckBox(parent=self)
        self.imageStackGlobalScale.setText("Global Scale")
        self.imageStackGlobalScale.stateChanged.connect(self.imageStackGlobalScaleChanged)
        self.imageStackBox.vbox.addWidget(self.imageStackGlobalScale)
        self.imageStackGlobalScale.minimum = None
        self.imageStackGlobalScale.maximum = None

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Selected Image:"))
        self.imageStackSubplotsSelected = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageStackSubplotsSelected)
        self.imageStackBox.vbox.addLayout(hbox)
        
        self.imageStackBox.hide()

        self.displayBox = QtGui.QGroupBox("Display Properties");
        self.displayBox.vbox = QtGui.QVBoxLayout()
        self.displayBox.setLayout(self.displayBox.vbox)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Gamma:"))
        self.displayGamma = QtGui.QDoubleSpinBox(parent=self)
        self.displayGamma.setValue(0.25);
        self.displayGamma.setSingleStep(0.25);
        self.displayGamma.valueChanged.connect(self.parent.view.updateTextures)
        hbox.addWidget(self.displayGamma)
        self.displayBox.vbox.addLayout(hbox)

        self.imageBox = QtGui.QGroupBox("Image Properties");
        self.imageBox.vbox = QtGui.QVBoxLayout()
        self.imageBox.setLayout(self.imageBox.vbox)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Min:"))
        self.imageMin = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageMin)
        self.imageBox.vbox.addLayout(hbox)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Max:"))
        self.imageMax = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageMax)
        self.imageBox.vbox.addLayout(hbox)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Sum:"))
        self.imageSum = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageSum)
        self.imageBox.vbox.addLayout(hbox)

        self.imageBox.hide()
        
        self.vbox.addWidget(self.generalBox)
        self.vbox.addWidget(self.imageStackBox)
        self.vbox.addWidget(self.imageBox)
        self.vbox.addWidget(self.displayBox)
        self.vbox.addStretch()
        self.setLayout(self.vbox)
        self.plots = 1
    def setDataset(self,data):
        self.imageStackGlobalScale.minimum = None
        self.imageStackGlobalScale.maximum = None

        self.data = data
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
            
    def clearDataset(self):
        string = "Dimensions: "
        self.dimensionality.setText(string)
        self.datatype.setText("Data Type: ")
        self.datasize.setText("Data Size: ")
        self.dataform.setText("Data Form: ")
        self.imageStackBox.hide()

    def imageStackSliceChanged(self,slice):
        self.recalculateSelectedSlice()
        self.parent.view.clear()
        for x in range(0,self.plots):
            for y in range(0,self.plots):
                if(slice+x+y*self.plots < self.data.shape[0]):
                    self.parent.view.imshow(self.data[slice+x+y*self.plots,:,:],subplot_x=x,subplot_y=y,update=False)
                    self.parent.statusBar.showMessage("Loaded slice %d" % (slice+x+y*self.plots),1000)
                else:
                    #clear subplot
                    pass
        self.parent.view.updateGL()
        self.parent.view.checkSelectedSubplot()

    def imageStackSubplotsChanged(self,plots):
        self.plots = plots
        self.imageStackSliceStep.setValue(plots*plots)
        self.imageStackSliceChanged(self.imageStackSlice.value())
#        self.parent.view.clear()

    def imageStackGlobalScaleChanged(self,state):
        if(self.imageStackGlobalScale.minimum == None):
            self.imageStackGlobalScale.minimum = numpy.min(self.data)
        if(self.imageStackGlobalScale.maximum == None):
            self.imageStackGlobalScale.maximum = numpy.max(self.data)
        self.imageStackSliceChanged(self.imageStackSlice.value())
    def recalculateSelectedSlice(self):
        plot = self.parent.view.selectedSubplot
        if(plot != None):
            s = self.plots*plot[1]+plot[0]+self.imageStackSlice.value()
            self.imageStackSubplotsSelected.setText(str(s))
        else:
            self.imageStackSubplotsSelected.setText(str(plot))

        
        
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
                    button_2D = msgBox.addButton(self.tr("2D series"), QtGui.QMessageBox.RejectRole);
                    button_3D = msgBox.addButton(self.tr("3D volume"), QtGui.QMessageBox.AcceptRole);
                res = msgBox.exec_();
                if(msgBox.clickedButton() == button_2D):
                    self.parent.view.loadStack(data)
#                    self.parent.view.imshow(data[0,:,:])
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
    def buildTree(self,filename):
        self.clear();
        self.datasets = {}
        self.setColumnCount(2)
        self.f = h5py.File(filename, "r")
        item = QtGui.QTreeWidgetItem(QtCore.QStringList("/"))
        self.addTopLevelItem(item)
        self.buildBranch(self.f,item)
        self.parent.view.clear()
        self.parent.datasetProp.clearDataset()
        self.loadData1()
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
        

class View(QtOpenGL.QGLWidget):
    def __init__(self,parent=None):
        QtOpenGL.QGLWidget.__init__(self,parent)
        self.translation = [0,0]
        self.zoom = 1.0
        self.setFocusPolicy(Qt.Qt.ClickFocus)
        self.data = {}
        self.texture = {}
        self.parent = parent
        self.setMouseTracking(True)
        self.dragging = False
        self.subplotBorder = 3
        self.selectedSubplot = None
        self.lastHoveredSubplot = None
        self.mode = None
        self.stackWidth = 1;
    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);
        glEnable(GL_BLEND);
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if(self.width() and self.height()):
            gluOrtho2D(0.0, self.width(), 0.0, self.height());
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

        self.visibleImages()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(self.width()/2.,self.height()/2.,0)
        glTranslatef(self.translation[0],self.translation[1],0)
        glScalef(4.0,4.0,1.0);
        glScalef(self.zoom,self.zoom,1.0);
        if(self.has_data):
            if(self.mode == "Stack"):
                pass
            else:
                for i,entry in enumerate(self.data):
                    data = self.data[entry]
                    img_width = data.shape[1]
                    img_height = data.shape[0]
                    glPushMatrix()
                    glTranslatef(-img_width/2.,-img_height/2.,0)
                    glTranslatef((img_width+self.subplotBorder)*entry[0],(img_height+self.subplotBorder)*entry[1],0)
                    glEnable(GL_TEXTURE_2D)
                    glBindTexture (GL_TEXTURE_2D, self.texture[entry]);
                    glColor3f(1.0,1.0,1.0);
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
                    if(entry == self.lastHoveredSubplot):
                        glColor3f(1.0,1.0,1.0);
                        glLineWidth(self.subplotBorder); 
                        glBegin(GL_LINES);
                        glVertex3f (0, img_height, 0.0);
                        glVertex3f (img_width, img_height, 0.0);
                        glVertex3f (img_width, img_height, 0.0);
                        glVertex3f (img_width, 0, 0.0);
                        glVertex3f (img_width, 0, 0.0);
                        glVertex3f (0, 0, 0.0);
                        glVertex3f (0, 0, 0.0);
                        glVertex3f (0, img_height, 0.0);
                        glEnd ();
                    elif(entry == self.selectedSubplot):
                        glColor3f(0.6,0.6,0.6);
                        glLineWidth(self.subplotBorder); 
                        glBegin(GL_LINES);
                        glVertex3f (0, img_height, 0.0);
                        glVertex3f (img_width, img_height, 0.0);
                        glVertex3f (img_width, img_height, 0.0);
                        glVertex3f (img_width, 0, 0.0);
                        glVertex3f (img_width, 0, 0.0);
                        glVertex3f (0, 0, 0.0);
                        glVertex3f (0, 0, 0.0);
                        glVertex3f (0, img_height, 0.0);
                    glEnd ();

                    glPopMatrix()
        glFlush()
    def imshow(self,data,subplot_x=0,subplot_y=0,update=True):
        self.data[(subplot_x,subplot_y)] = data
        offset = numpy.min(data);
        scale = float(numpy.max(data)-offset)
        if(scale == 0):
            scale = 1
        imageData = numpy.ones((data.shape[0],data.shape[1],3),dtype=numpy.uint8)
        gamma = self.parent.datasetProp.displayGamma.value();
        if(self.parent.datasetProp.imageStackBox.isVisible() and
           self.parent.datasetProp.imageStackGlobalScale.isChecked()):
            offset = self.parent.datasetProp.imageStackGlobalScale.minimum
            scale = float(self.parent.datasetProp.imageStackGlobalScale.maximum-offset)
        imageData[:,:,0] = 255*((data-offset)/scale)**(gamma)
        imageData[:,:,1] = 255*((data-offset)/scale)**(gamma)
        imageData[:,:,2] = 255*((data-offset)/scale)**(gamma)
        self.texture[(subplot_x,subplot_y)] = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture[(subplot_x,subplot_y)])
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, data.shape[1], data.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, imageData);
        self.has_data = True
        if(update):
            self.updateGL()
    def loadStack(self,data):
        self.mode = "Stack"
        self.data = data
        self.has_data = True
    def visibleImages(self):
        pos = (0,0)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT);
        (x,y,z) =  gluUnProject(pos[0], viewport[3]-pos[1],0 , model=modelview, proj=projection, view=viewport)
        x/(self.data.shape[2]+self.subplotBorder)
        x/(self.data.shape[2]+self.subplotBorder)
        print (x,y,z)
        pos = (self.width(),self.height())
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT);
        (x,y,z) =  gluUnProject(pos[0], viewport[3]-pos[1],0 , model=modelview, proj=projection, view=viewport)
        print (x,y,z)
        self.stackWidth

    def updateTextures(self):
        for i,entry in enumerate(self.data):
            data = self.data[entry]
            offset = numpy.min(data);
            scale = float(numpy.max(data)-offset)
            if(scale == 0):
                scale = 1
            imageData = numpy.ones((data.shape[0],data.shape[1],3),dtype=numpy.uint8)
            gamma = self.parent.datasetProp.displayGamma.value();
            if(self.parent.datasetProp.imageStackBox.isVisible() and
               self.parent.datasetProp.imageStackGlobalScale.isChecked()):
                offset = self.parent.datasetProp.imageStackGlobalScale.minimum
                scale = float(self.parent.datasetProp.imageStackGlobalScale.maximum-offset)
            imageData[:,:,0] = 255*((data-offset)/scale)**(gamma)
            imageData[:,:,1] = 255*((data-offset)/scale)**(gamma)
            imageData[:,:,2] = 255*((data-offset)/scale)**(gamma)
            self.texture[entry] = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.texture[entry])
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, data.shape[1], data.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, imageData);
        self.updateGL();
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
        elif(event.key() == Qt.Qt.Key_F):
            self.parent.statusBar.showMessage("Flaged "+str(self.hoveredSubplot()),1000)
    def mouseReleaseEvent(self, event):
        self.dragging = False
        if(event.pos() == self.dragStart and event.button() == QtCore.Qt.LeftButton):
            self.selectedSubplot = self.lastHoveredSubplot
            self.parent.datasetProp.recalculateSelectedSlice()
            if(self.selectedSubplot is not None):
                self.parent.datasetProp.imageMin.setText(str(numpy.min(self.data[self.selectedSubplot])))
                self.parent.datasetProp.imageMax.setText(str(numpy.max(self.data[self.selectedSubplot])))
                self.parent.datasetProp.imageSum.setText(str(numpy.sum(self.data[self.selectedSubplot])))
                self.parent.datasetProp.imageBox.show()
            else:
                self.parent.datasetProp.imageBox.hide()
            self.updateGL()
    def mousePressEvent(self, event):
        self.dragStart = event.pos()
        self.dragPos = event.pos()
        self.dragging = True
        self.updateGL()
    def mouseMoveEvent(self, event):
        if(self.dragging):
            self.translation[1] -= (event.pos()-self.dragPos).y()
            self.translation[0] += (event.pos()-self.dragPos).x()                        
            self.dragPos = event.pos()
            self.updateGL()
        ss = self.hoveredSubplot()
        if(ss != self.lastHoveredSubplot):
            self.lastHoveredSubplot = ss
            self.updateGL()
    def checkSelectedSubplot(self):
        if(self.selectedSubplot not in self.data.keys()):
            self.selectedSubplot = None
            self.parent.datasetProp.recalculateSelectedSlice()
    def hoveredSubplot(self):
        pos = self.mapFromGlobal(QtGui.QCursor.pos())
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT);
        (x,y,z) =  gluUnProject(pos.x(), viewport[3]-pos.y(),0 , model=modelview, proj=projection, view=viewport)
        plot = self.posToSubplot(x,y,z)
        if(plot in self.data.keys()):
            return plot    
        else:
            return None

    def posToSubplot(self,x,y,z):
        if(len(self.data.keys()) > 0):
            shape = self.data.values()[0].shape
            return (int(numpy.round(x/(shape[1]+self.subplotBorder))),int(numpy.round(y/(shape[0]+self.subplotBorder))))
    def scaleZoom(self,ratio):
        self.zoom *= ratio
        self.translation[0] *= ratio
        self.translation[1] *= ratio           
        self.updateGL()
    def clear(self):
        self.has_data = False
        self.data = {}
        glDeleteTextures(self.texture.values())
        self.texture = {}
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
        self.resize(800,450)
        settings = QtCore.QSettings()
        self.restoreGeometry(settings.value("geometry").toByteArray());
        self.restoreState(settings.value("windowState").toByteArray());
        QtCore.QTimer.singleShot(0,self.after_show)

    def after_show(self):
        if(len(sys.argv) > 1):
            self.tree.buildTree(sys.argv[1])
        
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
        fileName = QtGui.QFileDialog.getOpenFileName(self,"Open CXI File", QtCore.QString(), "CXI Files (*.cxi)");
        if(not fileName.isEmpty()):
            self.tree.buildTree(str(fileName))
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
                          


QtCore.QCoreApplication.setOrganizationName("CXIDB");
QtCore.QCoreApplication.setOrganizationDomain("cxidb.org");
QtCore.QCoreApplication.setApplicationName("CXI Viewer");
app = QtGui.QApplication(sys.argv)
aw = Viewer()
aw.show()
sys.exit(app.exec_())
