from OpenGL.GL import *
from OpenGL.GLU import *
#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
import numpy
import math
from matplotlib import colors
from matplotlib import cm
import pyqtgraph

class View(object):
    def __init__(self,parent=None):
        self.parent = parent
        self.setData()
        self.setMask()
        self.setSortingIndices()
    # DATA
    def setData(self,data=None):
        self.data = data
        if self.data != None:
            self.has_data = True
        else:
            self.has_data = False
    def getData(self,nDims=2,img_sorted=0):
        if self.data == None:
            return None
        elif nDims == 1:
            return numpy.array(self.data).flatten()
        elif nDims == 2:
            if self.data.isCXIStack():
                return numpy.array(self.data[img_sorted,:,:])
            else:
                return numpy.array(self.data[:,:])
    # MASK
    def setMask(self,maskDataset=None,maskOutBits=0):
        self.mask = maskDataset
        self.maskOutBits = maskOutBits
    def getMask(self,nDims=2,img_sorted=0):
        if self.mask == None:
            return None
        elif nDims == 2:
            if self.mask.isCXIStack():
                mask = self.mask[img_sorted,:,:]
            else:
                mask = self.mask[:,:]        
            return ((mask & self.maskOutBits) == 0)
    # SORTING
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

class View1D(View,pyqtgraph.PlotWidget):
    def __init__(self,parent=None):
        View.__init__(self,parent)
        pyqtgraph.PlotWidget.__init__(self,parent)
    #def loadData(self,dataset):
    #    self.setData(dataset)


class FunctionNorm(colors.Normalize):
    def __init__(self, normFunction, vmin=None, vmax=None, clip=False):
        colors.Normalize.__init__(self,vmin,vmax,clip)
        self.function = normFunction
        self.clip = clip
    def __call__(self,value,clip=None):
        clip = self.clip
        value_clipped = numpy.array(value,dtype="float")
        mask = numpy.isfinite(value_clipped) == False
        fvmin = self.function(self.vmin)
        fvmax = self.function(self.vmax)
        # check validity of given vmin and vmax
        if self.vmin > self.vmax or not numpy.isfinite(fvmin) or not numpy.isfinite(fvmax):
            return numpy.ma.array(zeros_like(value),mask=ones_like(value),fill_value=1e+20)
        # clipping / masking for values out of range
        above = value_clipped > self.vmax
        if above.sum() > 0:
            if clip: value_clipped[above] = self.vmax
            else: mask |= above
        below = value_clipped < self.vmin
        if below.sum() > 0:
            if clip: value_clipped[below] = self.vmin
            else: mask |= below
        # apply norm function
        outvalue = self.function(value_clipped)
        # masking for invalid values
        invalid = numpy.isfinite(outvalue) == False
        if invalid.sum() > 0:
            mask |= invalid
        # scale to interval 0 to 1
        outvalue = (outvalue-fvmin)/(fvmax-fvmin)
        return numpy.ma.array(outvalue,mask=mask,fill_value=1e+20)

class ImageLoader(QtCore.QObject):
    imageLoaded = QtCore.Signal(int) 
    def __init__(self,parent = None,view = None):
        QtCore.QObject.__init__(self,parent)  
        self.view = view
        self.loaded = {}
        self.imageData = {}
        self.mappable = cm.ScalarMappable()
        self.setNorm()
        self.setColormap()
    @QtCore.Slot(int,int)
    def loadImage(self,img):
        if(img in self.loaded):
           return
        self.loaded[img] = True
        img_sorted = self.view.getSortedIndex(img)
        data = self.view.getData(2,img_sorted)
        mask = self.view.getMask(2,img_sorted)
        self.imageData[img] = numpy.ones((self.view.data.getCXIHeight(),self.view.data.getCXIWidth(),4),dtype=numpy.uint8)
        self.imageData[img][:,:,:] = self.mappable.to_rgba(data,None,True)[:,:,:]
        if mask!=None:
            self.imageData[img][:,:,3] = 255*mask
        self.imageLoaded.emit(img)
    def clear(self):
        self.loaded = {}
    # COLORMAP
    def setColormap(self,colormapName='jet'):
        self.mappable.set_cmap(colormapName)
    def setNorm(self,scaling='log',vmin=1.,vmax=10000.,gamma=1):
        self.normScaling = scaling
        if scaling == 'lin':
            f = lambda x: x
        elif scaling == 'pow':
            gamma = self.view.parent.datasetProp.displayGamma.value()
            f = lambda x: x**gamma
        elif scaling == 'log':
            f = lambda x: numpy.log10(x)
        norm = FunctionNorm(f,vmin,vmax,True)
        self.mappable.set_norm(norm)
        self.mappable.set_clim(vmin,vmax)

class View2D(View,QtOpenGL.QGLWidget):
    needsImage = QtCore.Signal(int)
    clearLoaderThread = QtCore.Signal(int)
    def __init__(self,parent=None):
        View.__init__(self,parent)
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
        self.stackWidth = 1;
        self.has_data = False
        self.imageData = {}

        self.loaderThread = ImageLoader(None,self)
        self.needsImage.connect(self.loaderThread.loadImage)
        self.loaderThread.imageLoaded.connect(self.generateTexture)
        self.clearLoaderThread.connect(self.loaderThread.clear)

        self.imageLoader = QtCore.QThread()
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
        img_width = self.data.getCXIWidth()
        img_height = self.data.getCXIHeight()
        glPushMatrix()
        (x,y,z) = self.imageToScene(img,imagePos='BottomLeft',withBorder=False)
        glTranslatef(x,y,z)
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
    def paintImage(self,img):
        img_width = self.data.getCXIWidth()
        img_height = self.data.getCXIHeight()
        glPushMatrix()

        (x,y,z) = self.imageToScene(img,imagePos='BottomLeft',withBorder=False)
        glTranslatef(x,y,z)

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
    def paintGL(self):
        '''
        Drawing routine
        '''
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        # Set GL origin in the middle of the widget
        glTranslatef(self.width()/2.,self.height()/2.,0)
        # Apply user defined translation
        glTranslatef(self.translation[0],self.translation[1],0)
        # Apply user defined zoom
        glScalef(self.zoom,self.zoom,1.0);
        # Put GL origin on the top left corner of the widget
        glTranslatef(-(self.width()/self.zoom)/2.,(self.height()/self.zoom)/2.,0)
        if(self.has_data):
            if(self.data.getCXIFormat() == 2):
                img_width = self.data.getCXIWidth()
                img_height = self.data.getCXIHeight()
                visible = self.visibleImages()
                self.updateTextures(visible)
                for i,img in enumerate(self.textureIds):
                    self.paintImage(img)
                for img in (set(visible) - set(self.textureIds)):
                    self.paintLoadingImage(img)
        glFlush()
    def addToStack(self,data):
        pass
    def loadStack(self,data):
        self.setData(data)
        self.setStackWidth(self.stackWidth)
    def loadImage(self,data):
        if(data.getCXIFormat() == 2):        
            self.setData(data)
            self.setStackWidth(self.stackWidth)
        else:
            print "3D images not supported."
            sys.exit(-1)
    def getNImages(self):
        if self.data.isCXIStack():
            return self.data.shape[0]
        else:
            return 1
    def visibleImages(self):
        visible = []
        if(self.has_data is False):
            return visible

        top_left = self.windowToImage(0,0,0,checkExistance=False,clip=False)
        bottom_right = self.windowToImage(self.width(),self.height(),0,checkExistance=False,clip=False)

        top_left = self.imageToCell(top_left)
        bottom_right = self.imageToCell(bottom_right)
        nImages = self.getNImages()
        for x in numpy.arange(0,self.stackWidth):
            for y in numpy.arange(max(0,math.floor(top_left[1])),math.floor(bottom_right[1]+1)):
                img = y*self.stackWidth+x
                if(img < nImages):
                    visible.append(y*self.stackWidth+x)
        return visible
    @QtCore.Slot(int)
    def generateTexture(self,img):
        imageData = self.loaderThread.imageData[img][:,:,:]
        texture = glGenTextures(1)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, imageData.shape[1], imageData.shape[0], 0, GL_RGBA, GL_UNSIGNED_BYTE, imageData);
        self.textureIds[img] = texture
        self.updateGL()
    def updateTextures(self,images):
        for img in images:
            if(img not in self.textureIds):
                self.needsImage.emit(img)
    def wheelEvent(self, event):    
        settings = QtCore.QSettings()    
        self.translation[1] -= event.delta()*float(settings.value("scrollDirection"))
        self.clipTranslation()
        self.updateGL()
        # Do not allow zooming
       # self.scaleZoom(1+(event.delta()/8.0)/360)

    def clipTranslation(self):
        # Translation is bounded by top_margin < translation < bottom_margin
        if(self.has_data):
            margin = self.subplotBorder*3
            img_height = (self.data.getCXIHeight()+self.subplotSceneBorder())*self.zoom
            top_margin = -margin
            if(self.translation[1] < top_margin):
                self.translation[1] = top_margin
            stack_height = (self.getNImages()/self.stackWidth+1)*img_height
            bottom_margin = max(0,stack_height+margin-self.height())
            if(self.translation[1] > bottom_margin):
                self.translation[1] = bottom_margin
    def keyPressEvent(self, event):
        delta = self.width()/20
        img_height =  self.data.getCXIHeight()*self.zoom+self.subplotBorder
        stack_height = math.ceil(((self.getNImages()-0.0001)/self.stackWidth))*img_height
        if(event.key() == QtCore.Qt.Key_Up):
            self.translation[1] -= delta
            self.clipTranslation()
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_Down):
            self.translation[1] += delta
            self.clipTranslation()
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_P):
            self.translation[1] -= img_height
            self.clipTranslation()
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_N):
            self.translation[1] += img_height
            self.clipTranslation()
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_PageUp):
            self.translation[1] -= img_height
            self.clipTranslation()
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_PageDown):
            self.translation[1] += img_height
            self.clipTranslation()
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_End):
            self.translation[1] = 0
            self.clipTranslation()
            self.updateGL()
        elif(event.key() == QtCore.Qt.Key_Home):
            self.translation[1] = -stack_height + img_height
            self.clipTranslation()
            self.updateGL()
        # elif(event.key() == QtCore.Qt.Key_Left):
        #     self.translation[0] += delta
        #     self.clipTranslation()
        #     self.updateGL()
        # elif(event.key() == QtCore.Qt.Key_Right):
        #     self.translation[0] -= delta
        #     self.clipTranslation()
        #     self.updateGL()
        # elif(event.key() == QtCore.Qt.Key_Plus):
        #     self.scaleZoom(1.05)
        # elif(event.key() == QtCore.Qt.Key_Minus):
        #     self.scaleZoom(0.95)
        elif(event.key() == QtCore.Qt.Key_F):
            self.parent.statusBar.showMessage("Flaged "+str(self.hoveredImage()),1000)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        if(event.pos() == self.dragStart and event.button() == QtCore.Qt.LeftButton):
            self.selectedImage = self.lastHoveredImage
            self.parent.datasetProp.onImageSelected(self.selectedImage)
# #            self.parent.datasetProp.recalculateSelectedSlice()
#             if(self.selectedImage is not None):
#                 self.parent.datasetProp.onImageSelected(self.selectedImage)
#                 self.parent.datasetProp.imageMin.setText(str(numpy.min(self.data[self.selectedImage])))
#                 self.parent.datasetProp.imageMax.setText(str(numpy.max(self.data[self.selectedImage])))
#                 self.parent.datasetProp.imageSum.setText(str(numpy.sum(self.data[self.selectedImage])))
#                 self.parent.datasetProp.imageBox.show()
#             else:
#                 self.parent.datasetProp.imageBox.hide()
            self.updateGL()
    def mousePressEvent(self, event):
        self.dragStart = event.pos()
        self.dragPos = event.pos()
        self.dragging = True
        self.updateGL()
    def mouseMoveEvent(self, event):
        if(self.dragging):
            self.translation[1] -= (event.pos()-self.dragPos).y()
            self.clipTranslation()
            if(QtGui.QApplication.keyboardModifiers().__and__(QtCore.Qt.ControlModifier)):
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

    # Returns the scene position of the image corresponding to the index given
    # By default the coordinate of the TopLeft corner of the image is returned
    # By default the border is considered part of the image
    def imageToScene(self,imgIndex,imagePos='TopLeft',withBorder=True):
        img_width = self.data.getCXIWidth()+self.subplotSceneBorder()
        img_height = self.data.getCXIHeight()+self.subplotSceneBorder()
        (col,row) = self.imageToCell(imgIndex)
        x = img_width*col
        y = -img_height*row
        z = 0
        if(imagePos == 'TopLeft'):
            if(not withBorder):
                x += self.subplotSceneBorder()/2.
                y -= self.subplotSceneBorder()/2.
        elif(imagePos == 'BottomLeft'):
            y -= img_height
            if(not withBorder):
                x += self.subplotSceneBorder()/2.
                y += self.subplotSceneBorder()/2.
        elif(imagePos == 'BottomRight'):
            x += img_width
            y -= img_height
            if(not withBorder):
                x -= self.subplotSceneBorder()/2.
                y += self.subplotSceneBorder()/2.
        elif(imagePos == 'TopRight'):
            x += img_width
            if(not withBorder):
                x -= self.subplotSceneBorder()/2.
                y -= self.subplotSceneBorder()/2.
        elif(imagePos == 'Center'):
            x += img_width/2.
            y -= img_height/2.
        else:
            raise('Unknown imagePos: %s' % (imagePos))
        return (x,y,z)
    # Returns the window position of the top left corner of the image corresponding to the index given
    def imageToWindow(self,imgIndex,imagePos='TopLeft',withBorder=True):
        (x,y,z) = self.imageToScene(imgIndex,imagePos,withBorder)
        return self.sceneToWindow(x,y,z)
    # Returns the window location of a given point in scene
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
    # Returns the index of the image that it at a particular window location
    def windowToImage(self,x,y,z,checkExistance=True, clip=True):
        if(self.has_data > 0):
            shape = (self.data.getCXIHeight(),self.data.getCXIWidth())
            modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
            projection = glGetDoublev(GL_PROJECTION_MATRIX)
            viewport = glGetIntegerv(GL_VIEWPORT);
            (x,y,z) =  gluUnProject(x, viewport[3]-y,z , model=modelview, proj=projection, view=viewport)
            
            (x,y) = (int(numpy.floor(x/(self.data.getCXIWidth()+self.subplotSceneBorder()))),int(numpy.floor(-y/(self.data.getCXIHeight()+self.subplotSceneBorder()))))
            if(clip and (x < 0 or x >= self.stackWidth or y < 0)):
                return None            
            if(checkExistance and x + y*self.stackWidth >= self.getNImages()):
                return None
            return x + y*self.stackWidth

    # Returns the column and row from an image index
    def imageToCell(self,img):
        if(img is None):
            return img
        return (img%self.stackWidth,int(img/self.stackWidth))


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
        # Calculate the zoom necessary for the given stack width to fill the current viewport width
        new_zoom = float(self.width()-width*self.subplotBorder)/(self.data.getCXIWidth()*width)
        self.scaleZoom(new_zoom/self.zoom)
    def clear(self):
        self.setData()
        self.setMask()
        self.setSortingIndices()
        self.clearLoaderThread.emit(0)
        self.clearTextures()
        self.updateGL()
    def clearTextures(self):
        glDeleteTextures(self.textureIds.values())
        self.textureIds = {}
        self.clearLoaderThread.emit(0)
    def setStackWidth(self,width):  
        ratio = float(self.stackWidth)/width 
        self.stackWidth = width 
        # If there's no data just set the width and return
        if(self.has_data is not True):        
            return

        # Now change the width and zoom to match
        self.stackWidth = width
        self.zoomFromStackWidth(width)            
        self.translation[1] = (self.translation[1] + self.height()/2.0)*ratio-self.height()/2.0
        self.clipTranslation()
        self.parent.view.updateGL()
    def stackSceneWidth(self,width):
        return 
    def subplotSceneBorder(self):
        return self.subplotBorder/self.zoom

    def displayChanged(self,foovalue=None):
        self.clearTextures()
        self.updateGL()
