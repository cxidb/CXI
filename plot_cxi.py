#!/usr/bin/env python

import h5py
import numpy as np
import math
import sys
import matplotlib.pyplot as plt

if len(sys.argv) != 2:
    print "Usage: plot_cxi.py <cxi file>";
    sys.exit(-1)
fileName = sys.argv[1]

# open the HDF5 CXI file for writing
f = h5py.File(fileName, "r")
entry_1 = f["entry_1"];
data_1 = entry_1["data_1"];
data = data_1["data"];

if len(data.shape) == 2:
    plt.imshow(data);
elif len(data.shape) == 1:
    plt.plot(data);
else:
    print "Error: Can only plot 1D or 2D datasets";
    sys.exit(-1)
plt.show();
