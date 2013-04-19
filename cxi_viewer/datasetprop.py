#from PyQt4 import QtGui, QtCore, QtOpenGL, Qt
from PySide import QtGui, QtCore, QtOpenGL
from operator import mul

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
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(QtGui.QLabel("Scaling:"))
        self.displayLin = QtGui.QRadioButton("Linear")
        self.displayLin.toggled.connect(self.displayScalingChanged)
        self.displayLog = QtGui.QRadioButton("Logarithmic")
        self.displayLog.toggled.connect(self.displayScalingChanged)
        self.displayPow = QtGui.QRadioButton("Power")
        self.displayPow.toggled.connect(self.displayScalingChanged)
        self.displayLog.setChecked(True)
        vbox.addWidget(self.displayLin)
        vbox.addWidget(self.displayLog)
        vbox.addWidget(self.displayPow)
        self.displayBox.vbox.addLayout(vbox)
        
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel("Gamma:"))
        self.displayGamma = QtGui.QDoubleSpinBox(parent=self)
        self.displayGamma.setValue(0.25);
        self.displayGamma.setSingleStep(0.25);
        self.displayGamma.valueChanged.connect(self.displayScalingChanged)
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
    def displayScalingChanged(self,value):
        self.parent.view.clearTextures()
        self.parent.view.updateGL()
