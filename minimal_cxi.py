#!/usr/bin/env python

import h5py
import numpy as np
import math

fileName = "minimal.cxi"
# open the HDF5 CXI file for writing
f = h5py.File(fileName, "w")

# create data
x = np.arange(-5, 5, 0.1)
y = np.arange(0, 5, 0.1)
xx, yy = np.meshgrid(x, y)
sinc = np.sin(xx**2+yy**2)/(xx**2+yy**2)

# populate the file with the classes tree    
entry_1 = f.create_group("entry_1")
data_1 = entry_1.create_group("data_1")
# write the data
data = data_1.create_dataset("data", data=sinc)

f.close()

