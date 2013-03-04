#!/usr/bin/env python
import h5py
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
from operator import mul
import numpy
import math

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
        hbox.addWidget(QtGui.QLabel("Width:"))
        self.imageStackSubplots = QtGui.QSpinBox(parent=self)
        self.imageStackSubplots.setMinimum(1)
#        self.imageStackSubplots.setMaximum(5)
        self.imageStackSubplots.valueChanged.connect(self.imageStackSubplotsChanged)    
        self.imageStackSubplots.setValue(4)            
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
        self.imageStackImageSelected = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageStackImageSelected)
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
        self.displayGamma.valueChanged.connect(self.displayGammaChanged)
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


    def imageStackSubplotsChanged(self,plots):
        self.plots = plots
        self.parent.view.setStackWidth(plots)
#        self.parent.view.clear()

    def imageStackGlobalScaleChanged(self,state):
        if(self.imageStackGlobalScale.minimum == None):
            self.imageStackGlobalScale.minimum = numpy.min(self.data)
        if(self.imageStackGlobalScale.maximum == None):
            self.imageStackGlobalScale.maximum = numpy.max(self.data)
        self.parent.view.clearTextures()
        self.parent.view.updateGL()
    def displayGammaChanged(self,value):
        self.parent.view.clearTextures()
        self.parent.view.updateGL()
        
        
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
                #msgBox = QtGui.QMessageBox();
                #msgBox.setText("Display data as a 2D series of images or as a 3D volume?");
                #if('axes' in self.datasets[str(item.text(2))].attrs.keys() is not None or data.shape[0] > (data.shape[1] + data.shape[2]) * 3 or
                #   data.shape[0] < (data.shape[1] + data.shape[2]) / 3):
                #    button_2D = msgBox.addButton(self.tr("2D slices"), QtGui.QMessageBox.AcceptRole);
                #    button_3D = msgBox.addButton(self.tr("Volume"), QtGui.QMessageBox.RejectRole);
                #else:
                #    button_2D = msgBox.addButton(self.tr("2D slices"), QtGui.QMessageBox.RejectRole);
                #    button_3D = msgBox.addButton(self.tr("Volume"), QtGui.QMessageBox.AcceptRole);
                #res = msgBox.exec_();
                #if(msgBox.clickedButton() == button_2D):
                #    self.parent.view.clear()
                #    self.parent.view.loadStack(data)
#               #     self.parent.view.imshow(data[0,:,:])
                #    self.parent.statusBar.showMessage("Loaded slice 0",1000)
                #    data.form = '2D Image Stack'
                #elif(msgBox.clickedButton() == button_3D):
                #    wrnBox = QtGui.QMessageBox();
                #    wrnBox.setText("CXI Viewer currently does not support the visualization of 3D volumes.")
                #    wrnBox.setInformativeText('Please use an alternative such as LLNL\'s excelent <a href="http://llnl.gov/visit">VisIt</a>.')
                #    wrnBox.setIcon(QtGui.QMessageBox.Warning)
                #    wrnBox.exec_();
                #    return
                #    data.form = '3D Image Volume'                    
                self.parent.view.clear()
                self.parent.view.loadStack(data)
                self.parent.statusBar.showMessage("Loaded slice 0",1000)
                data.form = '2D Image Stack'
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
        

class ImageLoader(QtCore.QObject):
    imageLoaded = QtCore.Signal(int) 
    def __init__(self,parent = None,view = None):
        QtCore.QObject.__init__(self,parent)  
        self.view = view
        self.imageData = {}
        self.loaded = {}
    @QtCore.Slot(int,int)
    def loadImage(self,img):
        if(img in self.loaded):
            return
        self.loaded[img] = True
        data = self.view.data[img,:]
        offset = float(numpy.min(data));
        scale = float(numpy.max(data)-offset)
        if(scale == 0):
            scale = 1
        self.imageData[img] = numpy.ones((data.shape[0],data.shape[1],3),dtype=numpy.uint8)
        gamma = self.view.parent.datasetProp.displayGamma.value();
        if(self.view.parent.datasetProp.imageStackBox.isVisible() and
           self.view.parent.datasetProp.imageStackGlobalScale.isChecked()):
            offset = self.view.parent.datasetProp.imageStackGlobalScale.minimum
            scale = float(self.view.parent.datasetProp.imageStackGlobalScale.maximum-offset)
        self.imageData[img][:,:,0] = 255*((data-offset)/scale)**(gamma)
        self.imageData[img][:,:,1] = 255*((data-offset)/scale)**(gamma)
        self.imageData[img][:,:,2] = 255*((data-offset)/scale)**(gamma)
        self.imageLoaded.emit(img)
    def clear(self):
        self.imageData = {}
        self.loaded = {}

class View(QtOpenGL.QGLWidget):
    needsImage = QtCore.Signal(int) 
    def __init__(self,parent=None):
        QtOpenGL.QGLWidget.__init__(self,parent)
        self.translation = [0,0]
        self.zoom = 4.0
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.data = {}
        self.texturesLoading = {}
        self.textureIds = {}
#        self.textureImages = {}
        self.texture = {}
        self.parent = parent
        self.setMouseTracking(True)
        self.dragging = False
        self.subplotBorder = 10
        self.selectedImage = None
        self.lastHoveredImage = None
        self.mode = None
        self.stackWidth = 1;
        self.has_data = False

        self.imageLoader = QtCore.QThread()
        self.loaderThread = ImageLoader(None,self)
        self.needsImage.connect(self.loaderThread.loadImage)
        self.loaderThread.imageLoaded.connect(self.generateTexture)
        self.loaderThread.moveToThread(self.imageLoader)    
        self.imageLoader.start()

        self.loadingImageAnimationFrame = 0
        self.loadingImageAnimationTimer = QtCore.QTimer()
        self.loadingImageAnimationTimer.timeout.connect(self.incrementLoadingImageAnimationFrame)
        self.loadingImageAnimationTimer.start(100)
    def stopThreads(self):
        while(self.imageLoader.isRunning()):
            self.imageLoader.quit()
            QtCore.QThread.sleep(1)
    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);
        glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST);
        glEnable(GL_LINE_SMOOTH);
        glEnable(GL_POLYGON_SMOOTH);
        glEnable(GL_POINT_SMOOTH);
        glEnable(GL_BLEND);
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if(self.width() and self.height()):
            gluOrtho2D(0.0, self.width(), 0.0, self.height());        
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        self.circle_image = QtGui.QImage(100,100,QtGui.QImage.Format_ARGB32_Premultiplied)
        painter = QtGui.QPainter(self.circle_image)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255,255,255)))
        painter.drawEllipse(0,0,100,100)
        painter.end()
        self.circle_texture = self.bindTexture(self.circle_image,GL_TEXTURE_2D,GL_RGBA,QtOpenGL.QGLContext.LinearFilteringBindOption)
    def resizeGL(self, w, h):
        '''
        Resize the GL window 
        '''
        if(self.has_data):
            self.setStackWidth(self.stackWidth) 

        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if(w and h):
            gluOrtho2D(0.0, w, 0.0, h);
                            
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity(); 

    def paintSelectedImageBorder(self,img_width,img_height):
        glPushMatrix()
        glShadeModel(GL_FLAT)
        glColor3f(1.0,1.0,1.0);
        glLineWidth(0.5/self.zoom)
        glBegin(GL_LINE_LOOP)
        glVertex3f (0, img_height, 0.0);
        v = 10.0/self.zoom
        vi = 0
        while(v < img_width):
            glVertex3f (v, img_height, 0.0);                            
            if(vi % 2):
                glColor3f(0.0,0.0,0.0);
            else:
                glColor3f(1.0,1.0,1.0);
            vi += 1
            v += 10.0/self.zoom 
        glColor3f(1.0,1.0,1.0);
        glVertex3f (img_width, img_height, 0.0);
        v = 10.0/self.zoom
        vi = 0
        while(v < img_height):
            glVertex3f (img_width, img_height-v, 0.0);                            
            if(vi % 2):
                glColor3f(0.0,0.0,0.0);
            else:
                glColor3f(1.0,1.0,1.0);
            vi += 1
            v += 10.0/self.zoom 
        glColor3f(1.0,1.0,1.0);
        glVertex3f (img_width, 0, 0.0);
        v = 10.0/self.zoom
        vi = 0
        while(v < img_width):
            glVertex3f (img_width-v, 0, 0.0);                            
            if(vi % 2):
                glColor3f(0.0,0.0,0.0);
            else:
                glColor3f(1.0,1.0,1.0);
            vi += 1
            v += 10.0/self.zoom 
        glColor3f(1.0,1.0,1.0);
        glVertex3f (0, 0, 0.0);
        v = 10.0/self.zoom
        vi = 0
        while(v < img_height):
            glVertex3f (0, v, 0.0);                            
            if(vi % 2):
                glColor3f(0.0,0.0,0.0);
            else:
                glColor3f(1.0,1.0,1.0);
            vi += 1
            v += 10.0/self.zoom 
        glEnd ();
        glPopMatrix()
    @QtCore.Slot()
    def incrementLoadingImageAnimationFrame(self):
        self.loadingImageAnimationFrame += 1
        self.updateGL()
    def drawRectangle(self,width,height,filled=True):
        if(filled):
            glBegin(GL_POLYGON)
        else:
            glBegin(GL_LINE_LOOP)
        glVertex3f (0, height, 0.0)
        glVertex3f (width, height, 0.0)
        glVertex3f (width, 0, 0.0)
        glVertex3f (0, 0, 0.0)
        glEnd()
    def drawDisk(self,center,radius,nsides=20,filled=True):
        if(filled):
            glEnable(GL_TEXTURE_2D)
            glBindTexture (GL_TEXTURE_2D, self.circle_texture);
            glBegin (GL_QUADS);
            glTexCoord2f (0.0, 1.0)
            glVertex3f (center[0]-radius, center[1]-radius, 0.0)
            glTexCoord2f (1.0, 1.0)
            glVertex3f (center[0]+radius, center[1]-radius, 0.0)
            glTexCoord2f (1.0, 0.0)
            glVertex3f (center[0]+radius, center[1]+radius, 0.0)
            glTexCoord2f (0.0, 0.0)
            glVertex3f (center[0]-radius, center[1]+radius, 0.0)
            glEnd ();
            glDisable(GL_TEXTURE_2D)
           # glPointSize(2*radius*self.zoom)
           # glEnable(GL_POINT_SMOOTH)
           # glBegin(GL_POINTS)
           # glVertex3f(center[0],center[1],0)
           # glEnd();
        else:
            glBegin(GL_LINE_LOOP)
            for side in range(0,nsides):
                angle = 2*math.pi*side/nsides
                glVertex3f(radius*math.cos(angle)+center[0],radius*math.sin(angle)+center[1],0)
            glEnd()
    def paintLoadingImage(self,img):
        frame = self.loadingImageAnimationFrame%24
        img_width = self.data.shape[2]
        img_height = self.data.shape[1]
        glPushMatrix()
        pos_x = img%self.stackWidth
        pos_y = math.floor(img/self.stackWidth)
        glTranslatef(self.subplotSceneBorder()/2.+(img_width+self.subplotSceneBorder())*pos_x,self.subplotSceneBorder()/2.+(img_height+self.subplotSceneBorder())*pos_y,0)
        # Draw a ball in the center                
        path_radius = min(img_width,img_height)/10.0
        path_center = (img_width/2.0,6*img_height/10.0)
        radius = min(img_width,img_height)/40.0
        ndisks = 8
        for i in range(0,ndisks): 
            angle = math.pi/2.0-2*math.pi*i/ndisks
            if(i > frame/3):
                continue
            elif(i == frame/3):        
                glColor3f((frame%3+1)/4.0,(frame%3+1)/4.0,(frame%3+1)/4.0);
            else:
                glColor3f(3/4.0,3/4.0,3/4.0);
            self.drawDisk((path_center[0]+math.cos(angle)*path_radius,path_center[1]+math.sin(angle)*path_radius),radius,100)
        glColor3f(2/4.0,2/4.0,2/4.0);
        self.drawRectangle(img_width,img_height,filled=False)
        font = QtGui.QFont()
        metrics = QtGui.QFontMetrics(font);
        width = metrics.width("Loading...");
        ratio = (img_width*self.zoom/4.0)/width
        font.setPointSize(font.pointSize()*ratio)
        glColor3f(3/4.0,3/4.0,3/4.0);
        self.renderText(3*img_width/8.0,3*img_height/10.0,0.0,"Loading...",font);
        glPopMatrix()
    def paintGL(self):
        '''
        Drawing routine
        '''
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(self.width()/2.,self.height()/2.,0)
        glTranslatef(self.translation[0],self.translation[1],0)
        glScalef(self.zoom,self.zoom,1.0);    
        if(self.has_data):
            if(self.mode == "Stack"):
                img_width = self.data.shape[2]
                img_height = self.data.shape[1]
                glTranslatef(-((img_width+self.subplotSceneBorder())*self.stackWidth)/2.,-((img_height+self.subplotSceneBorder())/2.),0)
                visible = self.visibleImages()
                self.updateTextures(visible)
                for i,img in enumerate(self.textureIds):
                    glPushMatrix()
                    pos_x = img%self.stackWidth
                    pos_y = math.floor(img/self.stackWidth)
                    glTranslatef(self.subplotSceneBorder()/2.+(img_width+self.subplotSceneBorder())*pos_x,self.subplotSceneBorder()/2.+(img_height+self.subplotSceneBorder())*pos_y,0)
                    glEnable(GL_TEXTURE_2D)
                    glBindTexture (GL_TEXTURE_2D, self.textureIds[img]);
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
                    if(img == self.lastHoveredImage):
                        glPushMatrix()
                        glColor3f(1.0,1.0,1.0);
                        glLineWidth(0.5/self.zoom)
                        glBegin(GL_LINE_LOOP)
                        glVertex3f (0, img_height, 0.0);
                        glVertex3f (img_width, img_height, 0.0);
                        glVertex3f (img_width, 0, 0.0);
                        glVertex3f (0, 0, 0.0);
                        glEnd ();
                        glPopMatrix()
                    elif(img == self.selectedImage):
                        self.paintSelectedImageBorder(img_width,img_height)
                    glPopMatrix()
                for img in (set(visible) - set(self.textureIds)):
                    self.paintLoadingImage(img)
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
    def addToStack(self,data):
        pass
    def loadStack(self,data):
        self.mode = "Stack"
        self.data = data
        self.has_data = True
        self.setStackWidth(self.stackWidth)
    def loadImage(self,data):
        print "Loading..."
        if(len(data.shape) == 2):        
            self.mode = "Stack"  
            self.data = numpy.array(data)      
            self.data = self.data.reshape((1,data.shape[0],data.shape[1]))
            self.has_data = True
        else:
            print "3D images not supported"
            sys.exit(-1)
    def visibleImages(self):
        visible = []
        if(self.has_data is False):
            return visible
        pos = (0,0)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT);
        (x,y,z) =  gluUnProject(pos[0], viewport[3]-pos[1],0 , model=modelview, proj=projection, view=viewport)
        top_left  = (x/(self.data.shape[2]+self.subplotSceneBorder()), y/(self.data.shape[1]+self.subplotSceneBorder()))
        pos = (self.width(),self.height())
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT);
        (x,y,z) =  gluUnProject(pos[0], viewport[3]-pos[1],0 , model=modelview, proj=projection, view=viewport)
        bottom_right  = (x/(self.data.shape[2]+self.subplotSceneBorder()), y/(self.data.shape[1]+self.subplotSceneBorder()))

        for x in numpy.arange(max(0,math.floor(top_left[0])),min(self.stackWidth,math.floor(bottom_right[0])+1)):
            for y in numpy.arange(max(0,math.floor(bottom_right[1])),math.floor(top_left[1]+1)):
                img = y*self.stackWidth+x
                if(img < self.data.shape[0]):
                    visible.append(y*self.stackWidth+x)
        return visible
    @QtCore.Slot(int)
    def generateTexture(self,img):
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.loaderThread.imageData[img].shape[1], self.loaderThread.imageData[img].shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, self.loaderThread.imageData[img]);
        self.textureIds[img] = texture
        self.updateGL()
    def updateTextures(self,images):
        for img in images:
            if(img not in self.textureIds):
                self.needsImage.emit(img)
    def wheelEvent(self, event):        
        self.translation[1] -= event.delta()
        if(self.has_data):
            margin = self.height()/2.0
            img_height = (self.data.shape[1]+self.subplotSceneBorder())*self.zoom
            if(self.translation[1] > (img_height-self.height())/2 + margin):
                self.translation[1] = (img_height-self.height())/2 + margin
            stack_height = math.ceil(self.data.shape[0]/self.stackWidth)*img_height
            if(self.translation[1] < -stack_height+self.height()/2-img_height/2 - margin):
                self.translation[1] = -stack_height+self.height()/2-img_height/2 - margin
        self.updateGL()
        # Do not allow zooming
       # self.scaleZoom(1+(event.delta()/8.0)/360)

    def keyPressEvent(self, event):
        delta = self.width()/20
        img_height =  self.data.shape[1]*self.zoom+self.subplotBorder
        if(event.key() == QtCore.Qt.Key_Up):
            self.translation[1] -= delta
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_Down):
            self.translation[1] += delta
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_P):
            self.translation[1] -= img_height
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_N):
            self.translation[1] += img_height
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_PageUp):
            self.translation[1] -= img_height
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_PageDown):
            self.translation[1] += img_height
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_Left):
            self.translation[0] += delta
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_Right):
            self.translation[0] -= delta
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_Plus):
            self.scaleZoom(1.05)
        elif(event.key() == QtCore.Qt.Key_Minus):
            self.scaleZoom(0.95)
        elif(event.key() == QtCore.Qt.Key_F):
            self.parent.statusBar.showMessage("Flaged "+str(self.hoveredImage()),1000)
    def mouseReleaseEvent(self, event):
        self.dragging = False
        if(event.pos() == self.dragStart and event.button() == QtCore.Qt.LeftButton):
            self.selectedImage = self.lastHoveredImage
            self.parent.datasetProp.imageStackImageSelected.setText(str(self.selectedImage))
#            self.parent.datasetProp.recalculateSelectedSlice()
            if(self.selectedImage is not None):
                self.parent.datasetProp.imageMin.setText(str(numpy.min(self.data[self.selectedImage])))
                self.parent.datasetProp.imageMax.setText(str(numpy.max(self.data[self.selectedImage])))
                self.parent.datasetProp.imageSum.setText(str(numpy.sum(self.data[self.selectedImage])))
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
            if(self.mode is not "Stack" or (QtGui.QApplication.keyboardModifiers().__and__(QtCore.Qt.ControlModifier))):
               self.translation[0] += (event.pos()-self.dragPos).x()
            self.dragPos = event.pos()
            self.updateGL()
        ss = self.hoveredImage()
        if(ss != self.lastHoveredImage):
            self.lastHoveredImage = ss
            self.updateGL()
    def checkSelectedSubplot(self):
        if(self.selectedImage not in self.data.keys()):
            self.selectedImage = None
            self.parent.datasetProp.recalculateSelectedSlice()
    def hoveredImage(self):
        pos = self.mapFromGlobal(QtGui.QCursor.pos())
        img = self.windowToImage(pos.x(),pos.y(),0)
        return img

    def sceneToWindow(self,x,y,z):
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT);
        (x,y,z) =  gluProject(x, y,z , model=modelview, proj=projection, view=viewport)
        return (x,viewport[3]-y,z)
    # Returns the x,y,z position of a particular window position
    def windowToScene(self,x,y,z):
            modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
            projection = glGetDoublev(GL_PROJECTION_MATRIX)
            viewport = glGetIntegerv(GL_VIEWPORT);
            (x,y,z) =  gluUnProject(x, viewport[3]-y,z , model=modelview, proj=projection, view=viewport)
            return (x,y,z)
    # Returns the image that it at a particular location
    def windowToImage(self,x,y,z,checkExistance=True):
        if(self.has_data > 0):
            shape = self.data.shape
            modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
            projection = glGetDoublev(GL_PROJECTION_MATRIX)
            viewport = glGetIntegerv(GL_VIEWPORT);
            (x,y,z) =  gluUnProject(x, viewport[3]-y,z , model=modelview, proj=projection, view=viewport)
            
            (x,y) = (int(numpy.floor(x/(shape[2]+self.subplotSceneBorder()))),int(numpy.floor(y/(shape[1]+self.subplotSceneBorder()))))
            if(x < 0 or x >= self.stackWidth or y < 0):
                return None            
            if(checkExistance and x + y*self.stackWidth >= self.data.shape[0]):
                return None
            return x + y*self.stackWidth
    def imageToCell(self,img):
        if(img is None):
            return img
        return ((img%self.stackWidth),int(img/self.stackWidth))
    def scaleZoom(self,ratio):
        self.zoom *= ratio
        self.translation[0] *= ratio
        self.translation[1] *= ratio           
        self.updateGL()
    # Calculate the appropriate zoom level such that the windows will exactly fill the viewport widthwise
    def zoomFromStackWidth(self,width):
        # We'll assume all images have the same size and the projection is isometric
        if(self.has_data is not True):
            return 1
        self.scaleZoom((self.width()-width*self.subplotBorder)/(width*(self.sceneToWindow(self.data.shape[1], self.data.shape[2],0)[0] - self.sceneToWindow(0,0,0)[0])))
    def clear(self):
        self.has_data = False
        self.data = {}
        self.clearTextures()
        self.updateGL()
        self.loaderThread.clear()
    def clearTextures(self):
        glDeleteTextures(self.textureIds.values())
        self.textureIds = {}
    def setStackWidth(self,width):
        self.stackWidth = width
        if(self.has_data is not True):
            return 1
        self.zoomFromStackWidth(width)
#        plot = self.imageToScene(self.windowToImage(self.width()/2,self.height()/2,0))
#        print plot
#        image = plot[0]+plot[1]*max(plot[0],self.parent.view.stackWidth)
        image = self.windowToImage(self.width()/2,self.height()/2,0,checkExistance=False)
        plot = self.imageToCell(image)
        
        if(image >= self.data.shape[0]):
            image = self.data.shape[0]-1
        if(image < 0):
            image = 0
        
        new_plot = self.imageToCell(image)
        self.translation[1] -= (self.sceneToWindow(0,plot[1],0)[1]-self.sceneToWindow(0,new_plot[1],0)[1])*(self.data.shape[1]+self.subplotSceneBorder())
        self.parent.view.updateGL()
    def stackSceneWidth(self,width):
        return 
    def subplotSceneBorder(self):
        return self.subplotBorder/self.zoom


        
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
        if(settings.contains("geometry")):
            self.restoreGeometry(settings.value("geometry"));
        if(settings.contains("windowState")):
            self.restoreState(settings.value("windowState"));
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
        fileName = QtGui.QFileDialog.getOpenFileName(self,"Open CXI File", None, "CXI Files (*.cxi)");
        if(fileName[0]):
            self.tree.buildTree(fileName[0])
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
ret = app.exec_()
aw.view.stopThreads()
sys.exit(ret)
