#!/usr/bin/env python

import h5py
import numpy as np
import math

fileName = "nexus.cxi"
# open the HDF5 CXI file for writing
f = h5py.File(fileName, "w")

f.attrs['NeXus_version'] = "4.3.0"
f.attrs['creator'] = "CXI2NeXus"

f.create_dataset("cxi_version",data=120)

# create data 1
x = np.arange(-5, 5, 0.1)
y = np.arange(0, 5, 0.1)
xx, yy = np.meshgrid(x, y)
sinc1 = np.sin(xx**2+yy**2)/(xx**2+yy**2)

# create data 2
x = np.arange(-1, 1, 0.02)
y = np.arange(0, 1, 0.02)
xx, yy = np.meshgrid(x, y)
sinc2 = np.sin(xx**2+yy**2)/(xx**2+yy**2)

# populate the file with the classes tree    
entry_1 = f.create_group("entry_1")
entry_1.create_dataset("experimental_identifier",data=
                       "LCLS_2009_Dec11_170451_21963")
entry_1.create_dataset("start_time",data=
                       "2009-12-11T17:04:51-0800")
entry_1.attrs['NX_class'] = "NXentry"

sample_1 = entry_1.create_group("sample_1")
sample_1.create_dataset("name",data="Mimivirus")
sample_1.attrs['NX_class'] = "NXsample"

instrument_1 = entry_1.create_group("instrument_1")
instrument_1.create_dataset("name",data="AMO")
instrument_1.attrs['NX_class'] = "NXinstrument"

source_1 = instrument_1.create_group("source_1")
energy = source_1.create_dataset("energy",data=2.8893e-16) # in J
energy.attrs['units'] = "J"
pulse_width = source_1.create_dataset("pulse_width",
                                      data=70e-15) # in s
pulse_width.attrs['units'] = "s"
source_1.attrs['NX_class'] = "NXsource"

detector_1 = instrument_1.create_group("detector_1")
distance = detector_1.create_dataset("distance",
                                     data=0.15) # in meters
distance.attrs['units'] = "m"
data = detector_1.create_dataset("data",data=sinc1)
data.attrs['signal'] = 1
data.attrs['units'] = "counts"
detector_1.attrs['NX_class'] = "NXdetector"

detector_2 = instrument_1.create_group("detector_2")
distance = detector_2.create_dataset("distance",data=0.65) # in meters
distance.attrs['units'] = "m"
data = detector_2.create_dataset("data",data=sinc2)
data.attrs['units'] = "counts"
detector_2.attrs['NX_class'] = "NXdetector"

data_1 = entry_1.create_group("data_1")
data_1["data"] = h5py.SoftLink('/entry_1/instrument_1/detector_1/data')
data_1.attrs['NX_class'] = "NXdata"

data_2 = entry_1.create_group("data_2")
data_2["data"] = h5py.SoftLink('/entry_1/instrument_1/detector_2/data')
data_2.attrs['NX_class'] = "NXdata"

f.close()

