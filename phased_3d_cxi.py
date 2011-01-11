#!/usr/bin/env python

import h5py
import numpy as np
import math

fileName = "phased_3d.cxi"
# open the HDF5 CXI file for writing
f = h5py.File(fileName, "w")
f.create_dataset("cxi_version",data=100)

# create data
xx, yy, zz = np.mgrid[-5:5:16j, -5:5:16j, -5:5:16j]
sinc = np.sin(xx**2+yy**2+zz**2)/(xx**2+yy**2+zz**2) + \
       1j*np.cos(xx**2+yy**2+zz**2)/(xx**2+yy**2+zz**2)


# populate the file with the classes tree    
entry_1 = f.create_group("entry_1")
sample_1 = entry_1.create_group("sample_1")
sample_1.create_dataset("name",data="Mimivirus")
image_1 = entry_1.create_group("image_1")
image_1.create_dataset("data",data=sinc)
image_1.create_dataset("data_type",data="electron density")
image_1.create_dataset("data_space",data="real")
image_1.create_dataset("image_size",
                       data=[1.65e-6,1.65e-6,1.65e-6])
source_1 = image_1.create_group("source_1")
source_1.create_dataset("energy",data=1803.4) # in eV
detector_1 = image_1.create_group("detector_1")
detector_1.create_dataset("distance",
                          data=0.15) # in meters
detector_1.create_dataset("x_pixel_size",
                          data=15e-6) # in meters
detector_1.create_dataset("y_pixel_size",
                          data=15e-6) # in meters
process_1 = image_1.create_group("process_1")
process_1.create_dataset("command",data="find_center -i"
                         " mimi_raw.cxi -o mimi_center.cxi")
process_2 = image_1.create_group("process_2")
process_2.create_dataset("command",data="phase_image"
                         " phasing.txt -i mimi_center.cxi"
                         " -o mimi_phased.cxi")
note_1 = process_2.create_group("note_1")
note_1.create_dataset("file_name",data="phasing.txt")
note_1.create_dataset("description",data="configuration text"
                      " file used for phasing")
note_1.create_dataset("data",data='algorithm = "HIO"')

data_1 = entry_1.create_group("data_1")
data_1["data"] = h5py.SoftLink('/entry_1/image_1/data')

f.close()

