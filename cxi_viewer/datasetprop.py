#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
from operator import mul
import numpy,ctypes
import h5py
from matplotlib import colors
from matplotlib import cm
#import pyqtgraph

def sizeof_fmt(num):
    for x in ['bytes','kB','MB','GB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    return "%3.1f %s" % (num, 'TB')
    

# Consistent function nomenclature:
# - settingBla,settingBlabla => class variables defining current setting
# - settingChanged           => signal for other instances to apply change of setting
# - setSetting               => stores setting specified in widgets to class variables settingBla,settingBlabla,...
# - emitSetting              => calls setSetting + emits signal settingChanged
#(- refreshSetting           => refreshes widgets that have dependencies on dataset )
# - clearSetting             => sets setting to default + refreshes setting if refreshSettingWidget exists
#
class DatasetProp(QtGui.QWidget):
    maskChanged = QtCore.Signal(h5py.Dataset,int)
    normChanged = QtCore.Signal(str,float,float,float)
    colormapChanged = QtCore.Signal(str)
    imageStackSubplotsChanged = QtCore.Signal(str)
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.parent = parent
        self.vbox = QtGui.QVBoxLayout()
        # scrolling
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
        # GENERAL PROPERTIES
        # properties: dataset
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
        # properties: image stack
        self.imageStackBox = QtGui.QGroupBox("Image Stack Properties");
        self.imageStackBox.vbox = QtGui.QVBoxLayout()
        self.imageStackBox.setLayout(self.imageStackBox.vbox)
        # setting: image stack plots width
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Width:"))
        self.imageStackSubplots = QtGui.QSpinBox(parent=self)
        self.imageStackSubplots.setMinimum(1)
#        self.imageStackSubplots.setMaximum(5)
        self.imageStackSubplots.valueChanged.connect(self.imageStackSubplotsChanged)    
        hbox.addWidget(self.imageStackSubplots)
        self.imageStackBox.vbox.addLayout(hbox)
        # properties: selected image
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Selected Image:"))
        self.imageStackImageSelected = QtGui.QLabel("None",parent=self)
        hbox.addWidget(self.imageStackImageSelected)
        self.imageStackBox.vbox.addLayout(hbox)
        # DISPLAY PROPERTIES
        self.displayBox = QtGui.QGroupBox("Display Properties");
        self.displayBox.vbox = QtGui.QVBoxLayout()
        # setting: NORM
        # normVmax
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Maximum value:"))
        self.displayMax = QtGui.QDoubleSpinBox(parent=self)
        self.displayMax.setMinimum(-1000000.)
        self.displayMax.setMaximum(1000000.)
        self.displayMax.setSingleStep(1.)
        hbox.addWidget(self.displayMax)
        self.displayBox.vbox.addLayout(hbox)
        # normVmin
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Minimum value:"))
        self.displayMin = QtGui.QDoubleSpinBox(parent=self)
        self.displayMin.setMinimum(-1000000.)
        self.displayMin.setMaximum(1000000.)
        self.displayMin.setSingleStep(1.)
        hbox.addWidget(self.displayMin)
        self.displayBox.vbox.addLayout(hbox)
        # normText
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(QtGui.QLabel("Scaling:"))
        self.displayLin = QtGui.QRadioButton("Linear")
        self.displayLog = QtGui.QRadioButton("Logarithmic")
        self.displayPow = QtGui.QRadioButton("Power")
        vbox.addWidget(self.displayLin)
        vbox.addWidget(self.displayLog)
        # normGamma
        hbox = QtGui.QHBoxLayout()
        self.displayGamma = QtGui.QDoubleSpinBox(parent=self)
        self.displayGamma.setValue(0.25);
        self.displayGamma.setSingleStep(0.25);
        self.displayGamma.valueChanged.connect(self.emitNorm)
        hbox.addWidget(self.displayPow)
        hbox.addWidget(self.displayGamma)        
        vbox.addLayout(hbox)
        self.displayBox.vbox.addLayout(vbox)
        # setting: COLORMAP
        # colormap
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
        self.displayColormap.currentIndexChanged.connect(self.emitColormap)
        hbox.addWidget(self.displayColormap)
        self.displayBox.vbox.addLayout(hbox)
        self.displayBox.setLayout(self.displayBox.vbox)
        # setting: MASK
        # maskMask
        self.maskBox = QtGui.QGroupBox("Mask out pixels");
        self.maskBox.vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Pixelmask:"))
        self.maskMask = QtGui.QComboBox(parent=self)
        hbox.addWidget(self.maskMask)
        self.maskBox.vbox.addLayout(hbox)
        # maskOutBits
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
        self.maskBox.vbox.addLayout(vbox)
        for maskKey in self.masksBoxes:
            vbox.addWidget(self.masksBoxes[maskKey])
        self.maskBox.setLayout(self.maskBox.vbox)
        # properties: IMAGE
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
        # add all widgets to main vbox
        self.vboxScroll.addWidget(self.generalBox)
        self.vboxScroll.addWidget(self.imageStackBox)
        self.vboxScroll.addWidget(self.imageBox)
        self.vboxScroll.addWidget(self.displayBox)
        self.vboxScroll.addWidget(self.maskBox)
        self.vboxScroll.addStretch()
        self.setLayout(self.vbox)
        # clear all settings
        self.clear()
        # connect signals
        self.displayMax.valueChanged.connect(self.emitNorm)
        self.displayMin.valueChanged.connect(self.emitNorm)
        self.displayLin.toggled.connect(self.emitNorm)        
        self.displayLog.toggled.connect(self.emitNorm)
        self.displayPow.toggled.connect(self.emitNorm)
        for maskKey in self.masksBoxes:
            self.masksBoxes[maskKey].stateChanged.connect(self.emitMask)
        self.maskMask.currentIndexChanged.connect(self.emitMask)
    def clear(self):
        self.clearDataset()
        self.clearImageStackSubplots()
        self.clearNorm()
        self.clearColormap()
        self.clearMask()
    # DATASET
    def setDataset(self,dataset=None):
        self.dataset = dataset
        if dataset != None:
            self.dataset = dataset
            string = "Dimensions: "
            for d in dataset.shape:
                string += str(d)+"x"
            string = string[:-1]
            self.dimensionality.setText(string)
            self.datatype.setText("Data Type: %s" % (dataset.dtype.name))
            self.datasize.setText("Data Size: %s" % sizeof_fmt(dataset.dtype.itemsize*reduce(mul,dataset.shape)))
            if dataset.isCXIStack():
                form = "%iD Data Stack" % dataset.getCXIFormat()
            else:
                form = "%iD Data" % dataset.getCXIFormat()
            self.dataform.setText("Data form: %s" % form)
            if dataset.isCXIStack():
                self.imageStackBox.show()
            else:
                self.imageStackBox.hide()
        else:
            self.clearDataset()
        self.refreshMask()
    def clearDataset(self):
        self.dataset = None
        self.dimensionality.setText("Dimensions: ")
        self.datatype.setText("Data Type: ")
        self.datasize.setText("Data Size: ")
        self.dataform.setText("Data Form: ")
        self.imageStackBox.hide()
    # VIEW
    def onImageSelected(self,selectedImage):
        self.imageStackImageSelected.setText(str(selectedImage))
        if(selectedImage is not None):
            self.imageMin.setText(str(numpy.min(self.data[selectedImage])))
            self.imageMax.setText(str(numpy.max(self.data[selectedImage])))
            self.imageSum.setText(str(numpy.sum(self.data[selectedImage])))
            self.imageBox.show()
        else:
            self.parent.datasetProp.imageBox.hide()
    # NORM
    def setNorm(self):
        self.normVmin = self.displayMin.value()
        self.normVmax = self.displayMax.value()
        if self.displayLin.isChecked():
            self.normScaling = "lin"
        elif self.displayLog.isChecked():
            self.normScaling = "log"
        else:
            self.normScaling = "pow"
        self.normGamma = self.displayGamma.value()
        if self.normScaling == "lin":
            pass
        elif self.normScaling == "log" and (self.normVmin > 0. and self.normVmax > 0):
            pass
        elif self.normScaling == "pow" and self.normGamma < 1 and (self.normVmin > 0. and self.normVmax > 0):
            pass
        else:
            self.normVmin = 1.
            self.normVmax = 1000.
        self.displayMin.setValue(self.normVmin)
        self.displayMax.setValue(self.normVmax)
    def emitNorm(self,foovalue=None):
        self.setNorm()
        self.normChanged.emit(self.normScaling,self.normVmin,self.normVmax,self.normGamma)
    def clearNorm(self):
        self.displayMin.setValue(1.)
        self.displayMax.setValue(1000.)
        self.displayGamma.setValue(0.25)
        self.displayLog.setChecked(True)
        self.setNorm()
    # COLORMAP
    def setColormap(self,foovalue=None):
        self.colormap = self.displayColormap.currentText()
    def emitColormap(self):
        self.setColormap()
        self.colormapChanged.emit(self.colormap)
    def clearColormap(self):
        self.displayColormap.setCurrentIndex(0)
        self.setColormap()
    # STACK
    def setImageStackSubplots(self,foovalue=None):
        self.plots = self.imageStackSubplots.value()
    def emitImageStackSubplots(self):
        self.setImageStackSubplots()
        self.imageStackSubplotsChanged.emit(self.plots)
    def clearImageStackSubplots(self):
        self.imageStackSubplots.setValue(1)
        self.setImageStackSubplots()
    # MASK
    def setMask(self):
        maskText = self.maskMask.currentText()
        if self.dataset != None and maskText != "none" and maskText != "":
            self.mask = self.dataset.getCXIMasks()[maskText]
        else:
            self.mask = None
        PIXELMASK_BITS = {'perfect' : 0,# PIXEL_IS_PERFECT
                          'invalid' : 1,# PIXEL_IS_INVALID
                          'saturated' : 2,# PIXEL_IS_SATURATED
                          'hot' : 4,# PIXEL_IS_HOT
                          'dead' : 8,# PIXEL_IS_DEAD
                          'shadowed' : 16, # PIXEL_IS_SHADOWED
                          'peakmask' : 32, # PIXEL_IS_IN_PEAKMASK
                          'ignore' : 64, # PIXEL_IS_TO_BE_IGNORED
                          'bad' : 128, # PIXEL_IS_BAD
                          'resolution' : 256, # PIXEL_IS_OUT_OF_RESOLUTION_LIMITS
                          'missing' : 512, # PIXEL_IS_MISSING
                          'halo' : 1024} # PIXEL_IS_IN_HALO
        self.maskOutBits = 0
        for maskKey in self.masksBoxes:
            if self.masksBoxes[maskKey].isChecked():
                self.maskOutBits |= PIXELMASK_BITS[maskKey]
    def emitMask(self,foovalue=None):
        self.setMask()
        self.maskChanged.emit(self.mask,self.maskOutBits)
    def clearMask(self):
        self.mask = None
        self.maskOutBits = 0
    def refreshMask(self):
        self.clearMask()
        self.maskMask.clear()
        self.maskMask.addItem("none")
        if self.dataset != None:
            for maskType in self.dataset.getCXIMasks().keys():
                self.maskMask.addItem(maskType)


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

