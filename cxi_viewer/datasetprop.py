#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
from operator import mul
import numpy,ctypes
from matplotlib import colors
from matplotlib import cm

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

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Maximum value:"))
        self.displayMax = QtGui.QDoubleSpinBox(parent=self)
        self.displayMax.setMinimum(-1000000.)
        self.displayMax.setMaximum(1000000.)
        self.displayMax.setValue(10000.)
        self.displayMax.setSingleStep(100.)
        self.displayMax.valueChanged.connect(self.displayChanged)
        hbox.addWidget(self.displayMax)
        self.displayBox.vbox.addLayout(hbox)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Minimum value:"))
        self.displayMin = QtGui.QDoubleSpinBox(parent=self)
        self.displayMin.setMinimum(-1000000.)
        self.displayMin.setMaximum(1000000.)
        self.displayMin.setValue(0.)
        self.displayMin.setSingleStep(100.)
        self.displayMin.valueChanged.connect(self.displayChanged)
        hbox.addWidget(self.displayMin)
        self.displayBox.vbox.addLayout(hbox)

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
        
        colormapIcons = paintColormapIcons()
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Colormap:"))
        self.displayColormap = QtGui.QComboBox(parent=self)
        self.displayColormap.addItem(colormapIcons.pop('jet'),'jet')
        self.displayColormap.addItem(colormapIcons.pop('hot'),'hot')        
        self.displayColormap.addItem(colormapIcons.pop('gray'),'gray')        
        for colormap in colormapIcons.keys():
            self.displayColormap.addItem(colormapIcons[colormap],colormap)
        self.displayColormap.currentIndexChanged.connect(self.displayChanged)
        hbox.addWidget(self.displayColormap)
        self.displayBox.vbox.addLayout(hbox)

        self.displayBox.setLayout(self.displayBox.vbox)

        self.maskPixBox = QtGui.QGroupBox("Masking out pixels");
        self.maskPixBox.vbox = QtGui.QVBoxLayout()

        vbox = QtGui.QVBoxLayout()
        self.maskInvalidPix = QtGui.QCheckBox("Invalid",parent=self)
        self.maskSaturatedPix = QtGui.QCheckBox("Saturated",parent=self)
        self.maskHotPix = QtGui.QCheckBox("Hot",parent=self)
        self.maskDeadPix = QtGui.QCheckBox("Dead",parent=self)
        self.maskShadowedPix = QtGui.QCheckBox("Shadowed",parent=self)
        self.maskPeakmaskPix = QtGui.QCheckBox("In peakmask",parent=self)
        self.maskIgnorePix = QtGui.QCheckBox("To be ignored",parent=self)
        self.maskBadPix = QtGui.QCheckBox("Bad",parent=self)
        self.maskResolutionPix = QtGui.QCheckBox("Out of resolution limits",parent=self)
        self.maskMissingPix = QtGui.QCheckBox("Missing",parent=self)
        self.maskHaloPix = QtGui.QCheckBox("In Halo",parent=self)
        vbox.addWidget(self.maskInvalidPix)
        vbox.addWidget(self.maskSaturatedPix)
        vbox.addWidget(self.maskHotPix)
        vbox.addWidget(self.maskDeadPix)
        vbox.addWidget(self.maskShadowedPix)
        vbox.addWidget(self.maskPeakmaskPix)
        vbox.addWidget(self.maskIgnorePix)
        vbox.addWidget(self.maskBadPix)
        vbox.addWidget(self.maskResolutionPix)
        vbox.addWidget(self.maskMissingPix)
        vbox.addWidget(self.maskHaloPix)
        self.maskPixBox.vbox.addLayout(vbox)

        self.maskPixBox.setLayout(self.maskPixBox.vbox)

        self.imageBox = QtGui.QGroupBox("Image Properties");
        self.imageBox.vbox = QtGui.QVBoxLayout()

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Max:"))
        self.imageMax = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageMax)
        self.imageBox.vbox.addLayout(hbox)

        self.imageBox.setLayout(self.imageBox.vbox)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Min:"))
        self.imageMin = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageMin)
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
        self.vbox.addWidget(self.maskPixBox)
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

    def displayChanged(self,value):
        self.parent.view.clearTextures()
        self.parent.view.updateGL()

def paintColormapIcons():
    N = 20
    a = numpy.outer(numpy.ones(shape=(N,)),numpy.linspace(0.,1.,N))
    maps=[m for m in cm.datad if not m.endswith("_r")]
    mappable = cm.ScalarMappable()
    mappable.set_norm(colors.Normalize())
    iconDict = {}
    for m in maps:
        mappable.set_cmap(m)
        a_rgb = mappable.to_rgba(a,None,True)[:,:,:]
        img = QtGui.QImage(N,N, QtGui.QImage.Format_RGB32)
        for x in xrange(N):
            for y in xrange(N):
                img.setPixel(x, y, QtGui.QColor(a_rgb[y,x,0],a_rgb[y,x,1],a_rgb[y,x,2]).rgb())       
        icon = QtGui.QIcon(QtGui.QPixmap.fromImage(img))
        iconDict[m] = icon
    return iconDict

        

