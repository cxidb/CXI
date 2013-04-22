from OpenGL.GL import *
from OpenGL.GLU import *
#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
import numpy
import math
from matplotlib import colors
from matplotlib import cm


class ImageLoader(QtCore.QObject):
    imageLoaded = QtCore.Signal(int) 
    def __init__(self,parent = None,view = None):
        QtCore.QObject.__init__(self,parent)  
        self.view = view
        self.imageData = {}
        self.loaded = {}
        self.mappable = cm.ScalarMappable()
        self.setNorm()
        self.setColormap()
        self.setPixelmask()
        self.setMaskOutBits()
        self.setSortingIndices()
        self.initialLoad = True
    @QtCore.Slot(int,int)
    def loadImage(self,img):
        if(img in self.loaded):
           return
        if self.initialLoad:
            self.update()
            self.intialLoad = False
        img_sorted = self.getSortedIndex(img)
        data = self.view.data[img_sorted,:]
        self.loaded[img] = True
        offset = float(numpy.min(data))
        scale = float(numpy.max(data)-offset)
        if(scale == 0):
            scale = 1
        self.imageData[img] = numpy.ones((data.shape[0],data.shape[1],4),dtype=numpy.uint8)
        if self.gamma != 1:
            data = numpy.array(data**self.gamma,dtype='int16')
        if(self.view.parent.datasetProp.imageStackBox.isVisible() and
           self.view.parent.datasetProp.imageStackGlobalScale.isChecked()):
            offset = self.view.parent.datasetProp.imageStackGlobalScale.minimum
            scale = float(self.view.parent.datasetProp.imageStackGlobalScale.maximum-offset)
        if self.normName == 'log' or self.normName == 'pow':
            data[data<self.mappable.get_clim()[0]] = self.mappable.get_clim()[0]
        self.imageData[img][:,:,:] = self.mappable.to_rgba(data,None,True)[:,:,:]
        if self.view.mask != None and not self.maskOutBits == 0:
            mask = self.getMask(img_sorted)
            self.imageData[img][:,:,3] = 255*((mask & self.maskOutBits) == 0)
        self.imageLoaded.emit(img)
    def getMask(self,img_sorted):
        if self.pixelmaskText == 'none':
            return None
        elif self.pixelmaskText == 'mask_shared':
            return self.view.mask[:]
        elif self.pixelmaskText == 'mask':
            return self.view.mask[img_sorted,:]
    def setColormap(self,name='jet'):
        self.mappable.set_cmap(name)
    def setNorm(self,name='log',vmin=1.,vmax=10000.):
        if name == 'lin':
            norm = colors.Normalize()
            self.gamma = 1
        elif name == 'pow':
            norm = colors.Normalize()
            self.gamma = self.view.parent.datasetProp.displayGamma.value()
        elif name == 'log':
            norm = colors.LogNorm()
            self.gamma = 1
        self.normName = name
        self.mappable.set_norm(norm)
        self.mappable.set_clim(vmin,vmax)
    def setPixelmask(self,pixelmaskText="none"):
        if hasattr(self.view.parent,'CXITreeTop'):
            if self.pixelmaskText != pixelmaskText and pixelmaskText != 'none':
                self.view.mask = self.view.parent.CXITreeTop.f[self.view.parent.CXITreeTop.currGroupName+'/'+pixelmaskText]
        if pixelmaskText == "none":
            self.view.mask = None
        self.pixelmaskText = pixelmaskText
    def setMaskOutBits(self,value=0):
        self.maskOutBits = value
    def setSortingIndices(self, data=None):
        if data != None:
            self.sortingIndices = numpy.argsort(data)
        else:
            self.sortingIndices = None
    def getSortedIndex(self,index):
        if self.sortingIndices != None:
            return self.sortingIndices[index]
        else:
            return index
    def update(self):
        if hasattr(self.view.parent,'datasetProp'):
            self.setColormap(self.view.parent.datasetProp.displayColormap.currentText())
            vmin = self.view.parent.datasetProp.displayMin.value()
            vmax = self.view.parent.datasetProp.displayMax.value()
            if vmin >= vmax:
                vmin = vmax - 1000.
                self.view.parent.datasetProp.displayMin.setValue(vmin)
            if self.view.parent.datasetProp.displayLin.isChecked():
                self.setNorm('lin',vmin,vmax)
            elif self.view.parent.datasetProp.displayLog.isChecked():
                if vmin <= 0.:
                    vmin = 1.
                    self.view.parent.datasetProp.displayMin.setValue(vmin)
                if vmax <= 0.:
                    vmax = vmin+10000.
                    self.view.parent.datasetProp.displayMax.setValue(vmax)
                self.setNorm('log',vmin,vmax)
            elif self.view.parent.datasetProp.displayPow.isChecked():
                self.setNorm('pow',vmin,vmax)
            else: print "ERROR: No Scaling chosen."
            self.setPixelmask(self.view.parent.datasetProp.maskPixelmask.currentText())
            maskOutBits = 0
            masksBoxes = self.view.parent.datasetProp.masksBoxes
            for maskKey in masksBoxes:
                if masksBoxes[maskKey].isChecked():
                    maskOutBits |= PIXELMASK_BITS[maskKey]
            self.setMaskOutBits(maskOutBits)
    def clear(self):
        self.imageData = {}
        self.loaded = {}
        self.intialLoad = True

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
#            glScalef(1., -1., 1.)      
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
#            glScalef(1., -1., 1.)                
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
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.loaderThread.imageData[img].shape[1], self.loaderThread.imageData[img].shape[0], 0, GL_RGBA, GL_UNSIGNED_BYTE, self.loaderThread.imageData[img]);
        self.textureIds[img] = texture
        self.updateGL()
    def updateTextures(self,images):
        for img in images:
            if(img not in self.textureIds):
                self.needsImage.emit(img)
    def wheelEvent(self, event):    
        settings = QtCore.QSettings()    
        self.translation[1] -= event.delta()*float(settings.value("scrollDirection"))
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
        stack_height = math.ceil(((self.data.shape[0]-0.0001)/self.stackWidth))*img_height
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
        elif(event.key() == QtCore.Qt.Key_End):
            self.translation[1] = 0
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_Home):
            self.translation[1] = -stack_height + img_height
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
        self.loaderThread.clear()
        self.loaderThread.update()
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



PIXEL_IS_PERFECT = 0
PIXEL_IS_INVALID = 1
PIXEL_IS_SATURATED = 2
PIXEL_IS_HOT = 4
PIXEL_IS_DEAD = 8
PIXEL_IS_SHADOWED = 16
PIXEL_IS_IN_PEAKMASK = 32
PIXEL_IS_TO_BE_IGNORED = 64
PIXEL_IS_BAD = 128
PIXEL_IS_OUT_OF_RESOLUTION_LIMITS = 256
PIXEL_IS_MISSING = 512
PIXEL_IS_IN_HALO = 1024

PIXELMASK_BITS = {'perfect' : PIXEL_IS_PERFECT,
                  'invalid' : PIXEL_IS_INVALID,
                  'saturated' : PIXEL_IS_SATURATED,
                  'hot' : PIXEL_IS_HOT,
                  'dead' : PIXEL_IS_DEAD,
                  'shadowed' : PIXEL_IS_SHADOWED,
                  'peakmask' : PIXEL_IS_IN_PEAKMASK,
                  'ignore' : PIXEL_IS_TO_BE_IGNORED,
                  'bad' : PIXEL_IS_BAD,
                  'resolution' : PIXEL_IS_OUT_OF_RESOLUTION_LIMITS,
                  'missing' : PIXEL_IS_MISSING,
                  'halo' : PIXEL_IS_IN_HALO}
