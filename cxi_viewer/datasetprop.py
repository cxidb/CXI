#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
from operator import mul
import numpy,ctypes
from matplotlib import colors
from matplotlib import cm
import pyqtgraph

def sizeof_fmt(num):
    for x in ['bytes','kB','MB','GB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    return "%3.1f %s" % (num, 'TB')
    
class DatasetProp(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.parent = parent
        self.vbox = QtGui.QVBoxLayout()

        self.vboxScroll = QtGui.QVBoxLayout()
        self.scrollWidget = QtGui.QWidget()
        self.scrollWidget.setLayout(self.vboxScroll)
        self.scrollArea = QtGui.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QtGui.QFrame.NoFrame)
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.vbox.addWidget(self.scrollArea)

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
        self.imageStackSubplots.setValue(1)            
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



        # hbox = QtGui.QHBoxLayout()
        # hbox.addWidget(QtGui.QLabel("Maximum value:"))
        # self.displayMax = QtGui.QDoubleSpinBox(parent=self)
        # self.displayMax.setMinimum(-1000000.)
        # self.displayMax.setMaximum(1000000.)
        # self.displayMax.setValue(10000.)
        # self.displayMax.setSingleStep(100.)
        # self.displayMax.valueChanged.connect(self.displayChanged)
        # hbox.addWidget(self.displayMax)
        # self.displayBox.vbox.addLayout(hbox)

        # hbox = QtGui.QHBoxLayout()
        # hbox.addWidget(QtGui.QLabel("Minimum value:"))
        # self.displayMin = QtGui.QDoubleSpinBox(parent=self)
        # self.displayMin.setMinimum(-1000000.)
        # self.displayMin.setMaximum(1000000.)
        # self.displayMin.setValue(0.)
        # self.displayMin.setSingleStep(100.)
        
        # hbox.addWidget(self.displayMin)
        # self.displayBox.vbox.addLayout(hbox)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(QtGui.QLabel("Scaling:"))
        self.displayLin = QtGui.QRadioButton("Linear")
        self.displayLin.toggled.connect(self.displayChanged)
        self.displayLog = QtGui.QRadioButton("Logarithmic")
        self.displayLog.toggled.connect(self.displayChanged)
        self.displayPow = QtGui.QRadioButton("Power")
        self.displayPow.toggled.connect(self.displayChanged)
        self.displayLog.setChecked(True)
        vbox.addWidget(self.displayLin)
        vbox.addWidget(self.displayLog)

        hbox = QtGui.QHBoxLayout()
        self.displayGamma = QtGui.QDoubleSpinBox(parent=self)
        self.displayGamma.setValue(0.25);
        self.displayGamma.setSingleStep(0.25);
        self.displayGamma.valueChanged.connect(self.displayChanged)
        hbox.addWidget(self.displayPow)
        hbox.addWidget(self.displayGamma)        
        vbox.addLayout(hbox)
        self.displayBox.vbox.addLayout(vbox)
        
        icon_width = 256/2
        icon_height = 10
        colormapIcons = paintColormapIcons(icon_width,icon_height)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Colormap:"))
        self.displayColormap = QtGui.QComboBox(parent=self)
        self.displayColormap.setIconSize(QtCore.QSize(icon_width,icon_height))
        self.displayColormap.addItem(colormapIcons.pop('jet'),'jet')
        self.displayColormap.addItem(colormapIcons.pop('hot'),'hot')        
        self.displayColormap.addItem(colormapIcons.pop('gray'),'gray')        
        for colormap in colormapIcons.keys():
            self.displayColormap.addItem(colormapIcons[colormap],colormap)
        self.displayColormap.currentIndexChanged.connect(self.displayChanged)
        hbox.addWidget(self.displayColormap)
        self.displayBox.vbox.addLayout(hbox)

        self.displayBox.setLayout(self.displayBox.vbox)

        self.maskBox = QtGui.QGroupBox("Mask out pixels");
        self.maskBox.vbox = QtGui.QVBoxLayout()

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Pixelmask:"))
        self.maskPixelmask = QtGui.QComboBox(parent=self)
        self.maskPixelmaskRefreshItems()
        self.maskPixelmask.currentIndexChanged.connect(self.maskChanged)
        hbox.addWidget(self.maskPixelmask)
        self.maskBox.vbox.addLayout(hbox)
        self.maskLoaded = "None"

        vbox = QtGui.QVBoxLayout()
        maskInvalidPix = QtGui.QCheckBox("Invalid",parent=self)    
        maskSaturatedPix = QtGui.QCheckBox("Saturated",parent=self)
        maskHotPix = QtGui.QCheckBox("Hot",parent=self)
        maskDeadPix = QtGui.QCheckBox("Dead",parent=self)
        maskShadowedPix = QtGui.QCheckBox("Shadowed",parent=self)
        maskPeakmaskPix = QtGui.QCheckBox("In peakmask",parent=self)
        maskIgnorePix = QtGui.QCheckBox("To be ignored",parent=self)
        maskBadPix = QtGui.QCheckBox("Bad",parent=self)
        maskResolutionPix = QtGui.QCheckBox("Out of resolution limits",parent=self)
        maskMissingPix = QtGui.QCheckBox("Missing",parent=self)
        maskHaloPix = QtGui.QCheckBox("In Halo",parent=self)
        self.masksBoxes = {'invalid' : maskInvalidPix,
                           'saturated' : maskSaturatedPix,
                           'hot' : maskHotPix,
                           'dead' : maskDeadPix,
                           'shadowed' : maskShadowedPix,
                           'peakmask' : maskPeakmaskPix,
                           'ignore' : maskIgnorePix,
                           'bad' : maskBadPix,
                           'resolution' : maskResolutionPix,
                           'missing' : maskMissingPix,
                           'halo' : maskHaloPix}
        for maskKey in self.masksBoxes:
            self.masksBoxes[maskKey].stateChanged.connect(self.maskChanged)
            vbox.addWidget(self.masksBoxes[maskKey])
        self.maskBox.vbox.addLayout(vbox)

        self.maskBox.setLayout(self.maskBox.vbox)

        self.imageBox = QtGui.QGroupBox("Image Properties");
        self.imageBox.vbox = QtGui.QVBoxLayout()

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Image Range:"))
        self.imageRange = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageRange)
        self.imageBox.vbox.addLayout(hbox)

        self.imageBox.setLayout(self.imageBox.vbox)

        # hbox = QtGui.QHBoxLayout()
        # hbox.addWidget(QtGui.QLabel("Min:"))
        # self.imageMin = QtGui.QLabel("None",parent=self)
        # hbox.addWidget(self.imageMin)
        # self.imageBox.vbox.addLayout(hbox)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Image Sum:"))
        self.imageSum = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageSum)
        self.imageBox.vbox.addLayout(hbox)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Display Range:"))
        self.displayMin = QtGui.QDoubleSpinBox(parent=self)
        self.displayMin.editingFinished.connect(self.displayChanged)
        self.displayMax = QtGui.QDoubleSpinBox(parent=self)
        self.displayMax.editingFinished.connect(self.displayChanged)
        hbox.addWidget(self.displayMin)
        hbox.addWidget(QtGui.QLabel("to"))
        hbox.addWidget(self.displayMax)    
        self.imageBox.vbox.addLayout(hbox)

        self.intensityHistogram = pyqtgraph.PlotWidget()
        self.intensityHistogram.hideAxis('left')
        self.intensityHistogram.hideAxis('bottom')
#        self.intensityHistogram.setBackground(background=None)
        self.intensityHistogram.setFixedHeight(50)
        self.imageBox.vbox.addWidget(self.intensityHistogram)

        self.imageBox.hide()
        
        self.vboxScroll.addWidget(self.generalBox)
        self.vboxScroll.addWidget(self.imageStackBox)
        self.vboxScroll.addWidget(self.imageBox)
        self.vboxScroll.addWidget(self.displayBox)
        self.vboxScroll.addWidget(self.maskBox)
        self.vboxScroll.addStretch()
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

    def displayChanged(self,value):
        self.parent.view.clearTextures()
        self.parent.view.updateGL()

    def maskChanged(self,value):
        self.displayChanged(value)
        
    def maskPixelmaskRefreshItems(self):
        self.maskPixelmask.clear()
        self.maskPixelmask.addItem("none")
        if hasattr(self.parent,'CXINavigation'):
            if self.parent.CXINavigation.CXITreeTop.currGroupName != None:
                print self.parent.CXINavigation.CXITreeTop.f.items()
                datasets = self.parent.CXINavigation.CXITreeTop.f[self.parent.CXINavigation.CXITreeTop.currGroupName].keys()
                if 'mask_shared' in datasets:
                    self.maskPixelmask.addItem("mask_shared")
                    if 'mask' in datasets:
                        self.maskPixelmask.addItem("mask")

    def clear(self):
        self.maskPixelmaskRefreshItems()

    def onImageSelected(self,selectedImage):
        self.imageStackImageSelected.setText(str(selectedImage))
        if(selectedImage is not None):
            self.imageRange.setText("%d to %d" %(numpy.min(self.data[selectedImage]),numpy.max(self.data[selectedImage])))
#            self.imageMin.setText(str(numpy.min(self.data[selectedImage])))
#            self.imageMax.setText(str(numpy.max(self.data[selectedImage])))
            self.imageSum.setText(str(numpy.sum(self.data[selectedImage])))
            (hist,edges) = numpy.histogram(self.data[selectedImage],bins=100)
            self.intensityHistogram.clear()
            edges = (edges[:-1]+edges[1:])/2.0
            item = self.intensityHistogram.plot(edges,hist,fillLevel=0,fillBrush=QtGui.QColor(255, 255, 255, 128),antialias=True)
            self.intensityHistogram.setBackground(background=None)
            self.intensityHistogram.getPlotItem().getViewBox().setMouseEnabled(x=False,y=False)
            item.sigClicked.connect(self.onHistogramClicked)
#            self.intensityHistogram.getPlotItem().getViewBox().enableAutoRange(axis='bottom',enable=True)
#            self.intensityHistogram.getPlotItem().getViewBox().enableAutoRange(axis='left',enable=True)
            font = self.font()
            font.setPointSize(8)
            self.intensityHistogram.getPlotItem().getAxis('bottom').setTickFont(font) 
            region = pyqtgraph.LinearRegionItem(values=[edges[0],edges[-1]],brush="#ffffff15")
            region.setZValue(10)
            region.setBounds([edges[0],edges[-1]])
            region.sigRegionChangeFinished.connect(self.onHistogramClicked)
            self.intensityHistogram.addItem(region)
            self.imageBox.show()
        else:
            self.parent.datasetProp.imageBox.hide()
    def onHistogramClicked(self):
        print "here"
def paintColormapIcons(W,H):
    a = numpy.outer(numpy.ones(shape=(H,)),numpy.linspace(0.,1.,W))
    maps=[m for m in cm.datad if not m.endswith("_r")]
    mappable = cm.ScalarMappable()
    mappable.set_norm(colors.Normalize())
    iconDict = {}
    for m in maps:
        mappable.set_cmap(m)
        temp = mappable.to_rgba(a,None,True)[:,:,:]
        a_rgb = numpy.zeros(shape=(H,W,4),dtype=numpy.uint8)
        # For some reason we have to swap indices !? Otherwise inverted colors...
        a_rgb[:,:,2] = temp[:,:,0]
        a_rgb[:,:,1] = temp[:,:,1]
        a_rgb[:,:,0] = temp[:,:,2]
        a_rgb[:,:,3] = 0xff
        img = QtGui.QImage(a_rgb,W,H,QtGui.QImage.Format_ARGB32)
        icon = QtGui.QIcon(QtGui.QPixmap.fromImage(img))
        iconDict[m] = icon
    return iconDict

