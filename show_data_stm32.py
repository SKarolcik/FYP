#!/usr/bin/env python
__author__ = 'Stefan'
import sys
import os
import numpy as np

import time

import matplotlib.pyplot as plt
import matplotlib.animation as animation


f = open("stm_readings.dat", "r")
line_count = 0
frame = np.zeros((200,64))
#imv = MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix'])
#imv.setLevels(0,4095)
fig = plt.figure()
ims = []

lines = f.readlines()
for x in lines:
    if "Frame" in x:
        print x
        if not ("no: 0") in x:
            line_count = 0
            #imv.setImage(frame, autoRange=False, autoLevels=False, autoHistogramRange=False)
            im = plt.imshow(frame.reshape(64,200), animated=True)
            ims.append([im])
            #plt.show()
            #time.sleep(2)
            #frames.append(frame.reshape(64,200))
            #print frame
    else:
        vals = x.split(" ")
        for i in range(64):
            frame[line_count][i] = int(vals[i], 16)
        line_count = line_count + 1


ani = animation.ArtistAnimation(fig,ims,interval=400, repeat_delay=2000)

plt.show()
#self.imv = MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix'])
#self.imv.setLevels(0,250)