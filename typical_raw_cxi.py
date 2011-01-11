#!/usr/bin/env python

import h5py
import numpy as np
import math

fileName = "typical_raw.cxi"
# open the HDF5 CXI file for writing
f = h5py.File(fileName, "w")
f.create_dataset("cxi_version",data=100)

# create data 1
x = np.arange(-5, 5, 0.1)
y = np.arange(-5, 5, 0.2)
xx, yy = np.meshgrid(x, y)
sinc1 = np.sin(xx**2+yy**2)/(xx**2+yy**2)

# create data 2
x = np.arange(-1, 1, 0.02)
y = np.arange(-1, 1, 0.04)
xx, yy = np.meshgrid(x, y)
sinc2 = np.sin(xx**2+yy**2)/(xx**2+yy**2)


# populate the file with the classes tree    
entry_1 = f.create_group("entry_1")
entry_1.create_dataset("experimental_identifier",data="LCLS_2009_Dec11_170451_21963")
entry_1.create_dataset("start_time",data="2009-12-11T17:04:51-0800")
sample_1 = entry_1.create_group("sample_1")
sample_1.create_dataset("name",data="Mimivirus")
instrument_1 = entry_1.create_group("instrument_1")
instrument_1.create_dataset("name",data="AMO")
source_1 = instrument_1.create_group("source_1")
source_1.create_dataset("energy",data=1803.4) # in eV
source_1.create_dataset("pulse_width",data=70) # in fs

detector_1 = instrument_1.create_group("detector_1")
detector_1.create_dataset("distance",data=0.15) # in meters
detector_1.create_dataset("data",data=sinc1)

detector_2 = instrument_1.create_group("detector_2")
detector_2.create_dataset("distance",data=0.65) # in meters
detector_2.create_dataset("data",data=sinc2)

data_1 = entry_1.create_group("data_1")
data_1["data"] = h5py.SoftLink('/entry_1/instrument_1/detector_1/data')

data_2 = entry_1.create_group("data_2")
data_2["data"] = h5py.SoftLink('/entry_1/instrument_1/detector_2/data')

f.close()

