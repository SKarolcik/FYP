__author__ = 'Stefan'
import matplotlib
import numpy as np
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import os
import time

import threading
import Queue


file_out = open("out_readings.dat", "r")

avgs = np.zeros((780,1))
for j in range(780):
    frameFlattened = np.zeros((12800,1))
    count = 0
    for i in range(6400):
        pos = i*2
        val1 = file_out.readline()
        if not val1:
            break
        val1 = int(val1)
        #print hex(val1)
        val0 = val1 & 0xFFF
        val1 = val1 >> 16
        i0 = ((2.0 - (val0/4095.0)*2.5)/8.0)*1000
        i1 = ((2.0 - (val1/4095.0)*2.5)/8.0)*1000
        frameFlattened[pos] = i0
        frameFlattened[pos+1] = i1
    
    single_frame = frameFlattened
    avg = np.mean(single_frame[0])
    #print avg    
    avgs[j] = avg
    #print count
    #if count > 800 :
        #plt.imshow(single_frame, cmap='hot', interpolation='nearest',vmin=1,vmax=12800)
        #plt.show()
        
#single_frame = np.transpose(frameFlattened.reshape((200,64)))
#print np.amax(single_frame)
#print np.mean(single_frame)
#print np.amin(single_frame)

plt.plot(avgs)
#plt.imshow(single_frame, cmap='hot', interpolation='nearest',vmin=1,vmax=12800)
plt.show()


'''
for i in range(6400):
    exp = i*2
    word = (exp+1) + ((exp+2)<<16)
    writing = str(word) + '\n'
    file_out.write(writing)

'''


import collections


def cmapToColormap(cmap, nTicks=16):
    """
    Converts a Matplotlib cmap to pyqtgraphs colormaps. No dependency on matplotlib.

    Parameters:
    *cmap*: Cmap object. Imported from matplotlib.cm.*
    *nTicks*: Number of ticks to create when dict of functions is used. Otherwise unused.
    """

    # Case #1: a dictionary with 'red'/'green'/'blue' values as list of ranges (e.g. 'jet')
    # The parameter 'cmap' is a 'matplotlib.colors.LinearSegmentedColormap' instance ...
    if hasattr(cmap, '_segmentdata'):
        colordata = getattr(cmap, '_segmentdata')
        if ('red' in colordata) and isinstance(colordata['red'], collections.Sequence):
            # print("[cmapToColormap] RGB dicts with ranges")

            # collect the color ranges from all channels into one dict to get unique indices
            posDict = {}
            for idx, channel in enumerate(('red', 'green', 'blue')):
                for colorRange in colordata[channel]:
                    posDict.setdefault(colorRange[0], [-1, -1, -1])[idx] = colorRange[2]

            indexList = list(posDict.keys())
            indexList.sort()
            # interpolate missing values (== -1)
            for channel in range(3):  # R,G,B
                startIdx = indexList[0]
                emptyIdx = []
                for curIdx in indexList:
                    if posDict[curIdx][channel] == -1:
                        emptyIdx.append(curIdx)
                    elif curIdx != indexList[0]:
                        for eIdx in emptyIdx:
                            rPos = (eIdx - startIdx) / (curIdx - startIdx)
                            vStart = posDict[startIdx][channel]
                            vRange = (posDict[curIdx][channel] - posDict[startIdx][channel])
                            posDict[eIdx][channel] = rPos * vRange + vStart
                        startIdx = curIdx
                        del emptyIdx[:]
            for channel in range(3):  # R,G,B
                for curIdx in indexList:
                    posDict[curIdx][channel] *= 255

            posList = [[i, posDict[i]] for i in indexList]
            return posList

        # Case #2: a dictionary with 'red'/'green'/'blue' values as functions (e.g. 'gnuplot')
        elif ('red' in colordata) and isinstance(colordata['red'], collections.Callable):
            # print("[cmapToColormap] RGB dict with functions")
            indices = np.linspace(0., 1., nTicks)
            luts = [np.clip(np.array(colordata[rgb](indices), dtype=np.float), 0, 1) * 255 \
                    for rgb in ('red', 'green', 'blue')]
            return list(zip(indices, list(zip(*luts))))

    # If the parameter 'cmap' is a 'matplotlib.colors.ListedColormap' instance, with the attributes 'colors' and 'N'
    elif hasattr(cmap, 'colors') and hasattr(cmap, 'N'):
        colordata = getattr(cmap, 'colors')
        # Case #3: a list with RGB values (e.g. 'seismic')
        if len(colordata[0]) == 3:
            # print("[cmapToColormap] list with RGB values")
            indices = np.linspace(0., 1., len(colordata))
            scaledRgbTuples = [(rgbTuple[0] * 255, rgbTuple[1] * 255, rgbTuple[2] * 255) for rgbTuple in colordata]
            return list(zip(indices, scaledRgbTuples))

        # Case #3: a list of tuples with positions and RGB-values (e.g. 'terrain')
        # -> this section is probably not needed anymore!?
        elif len(colordata[0]) == 2:
            # print("[cmapToColormap] list with positions and RGB-values. Just scale the values.")
            scaledCmap = [(idx, (vals[0] * 255, vals[1] * 255, vals[2] * 255)) for idx, vals in colordata]
            return scaledCmap

    # Case #X: unknown format or datatype was the wrong object type
    else:
        raise ValueError("[cmapToColormap] Unknown cmap format or not a cmap!")
