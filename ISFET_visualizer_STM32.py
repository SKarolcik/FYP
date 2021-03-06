#!/usr/bin/env python
__author__ = 'Stefan'
import sys
import os
import numpy as np
import re

import threading
#import Queue
import queue
import time
#import collections
import collections.abc
import struct

from matplotlib import cm
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.exporters

FREQUENCY = 2000000

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


class MplCmapImageView(pg.ImageView):
    def __init__(self, additionalCmaps=[], setColormap=None, **kargs):
        super(MplCmapImageView, self).__init__(**kargs)

        self.gradientEditorItem = self.ui.histogram.item.gradient

        self.activeCm = "grey"
        self.mplCmaps = {}

        if len(additionalCmaps) > 0:
            self.registerCmap(additionalCmaps)

        if setColormap is not None:
            self.gradientEditorItem.restoreState(setColormap)



    def registerCmap(self, cmapNames):
        """ Add matplotlib cmaps to the GradientEditors context menu"""
        self.gradientEditorItem.menu.addSeparator()
        savedLength = self.gradientEditorItem.length
        self.gradientEditorItem.length = 100

        # iterate over the list of cmap names and check if they're avaible in MPL
        for cmapName in cmapNames:
            if not hasattr(cm, cmapName):
                print('[extendedimageview] Unknown cmap name: \'{}\'. Your Matplotlib installation might be outdated.'.format(cmapName))
            else:
                # create a Dictionary just as the one at the top of GradientEditorItem.py
                cmap = getattr(cm, cmapName)
                self.mplCmaps[cmapName] = {'ticks': cmapToColormap(cmap), 'mode': 'rgb'}

                # Create the menu entries
                # The following code is copied from pyqtgraph.ImageView.__init__() ...
                px = QtGui.QPixmap(100, 15)
                p = QtGui.QPainter(px)
                self.gradientEditorItem.restoreState(self.mplCmaps[cmapName])
                grad = self.gradientEditorItem.getGradient()
                brush = QtGui.QBrush(grad)
                p.fillRect(QtCore.QRect(0, 0, 100, 15), brush)
                p.end()
                label = QtGui.QLabel()
                label.setPixmap(px)
                label.setContentsMargins(1, 1, 1, 1)
                act = QtGui.QWidgetAction(self.gradientEditorItem)
                act.setDefaultWidget(label)
                act.triggered.connect(self.cmapClicked)
                act.name = cmapName
                self.gradientEditorItem.menu.addAction(act)
        self.gradientEditorItem.length = savedLength


    def cmapClicked(self, b=None):
        """onclick handler for our custom entries in the GradientEditorItem's context menu"""
        act = self.sender()
        self.gradientEditorItem.restoreState(self.mplCmaps[act.name])
        self.activeCm = act.name


class GuiViewer(QtGui.QWidget):

    def __init__(self):
        super(GuiViewer, self).__init__()

        self.initUI()

    def initUI(self):


        self.sendSPIBtn = QtGui.QPushButton("Select file")
        self.startBtn = QtGui.QPushButton("Start visualization")
        self.quitBtn = QtGui.QPushButton("Quit")
        self.threadBtn = QtGui.QPushButton("Stop thread")
        self.refBtn = QtGui.QPushButton("Set reference")
        self.clearBtn = QtGui.QPushButton("Clear reference")
        self.getFilenameEdit = QtGui.QLineEdit(self)

        self.saveBox = QtGui.QCheckBox("Save images")

        self.frameLb = QtGui.QLabel('N = N/A')

        self.logo = QtGui.QLabel(self)
        pixmap = QtGui.QPixmap('logo_with_desc.png')
        self.logo.setPixmap(pixmap.scaled(501,200,QtCore.Qt.KeepAspectRatio))

        #self.imv = pg.ImageView()
        self.imv = MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix'])
        self.imv.setLevels(0,250)

        self.exporter = pg.exporters.ImageExporter(self.imv.imageItem)
        self.exporter.params.param('width').setValue(1920, blockSignal=self.exporter.widthChanged)
        self.exporter.params.param('height').setValue(1080, blockSignal=self.exporter.heightChanged)
        #self.exporter.parameters()['width'] = 100
        
        self.win = pg.GraphicsWindow(title="Average sensor value")
        self.win.resize(1200,50)
        self.avgVal = self.win.addPlot()
        self.curve = self.avgVal.plot()
        self.avgValVect = []

        self.exporter_line = pg.exporters.ImageExporter(self.avgVal)
        self.exporter_line.params.param('width').setValue(1920, blockSignal=self.exporter_line.widthChanged)
        self.exporter_line.params.param('height').setValue(1080, blockSignal=self.exporter_line.heightChanged)
        
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.logo, 1, 0, 4, 1)
        grid.addWidget(self.sendSPIBtn, 1, 1)
        grid.addWidget(self.getFilenameEdit, 1, 2)
        grid.addWidget(self.saveBox, 2, 2)
        grid.addWidget(self.startBtn, 1, 3)
        grid.addWidget(self.threadBtn, 2, 3)
        grid.addWidget(self.quitBtn, 2, 4)
        grid.addWidget(self.refBtn, 3, 3)
        grid.addWidget(self.clearBtn, 3, 4)
        grid.addWidget(self.frameLb, 5, 3)


        grid.addWidget(self.imv, 6, 0, 4, 5)
        
        grid.addWidget(self.win, 11, 0, 4, 5)
        

        self.setLayout(grid)

        self.setGeometry(250, 100, 1200, 900)
        self.setWindowTitle('ISFET viewer')    
        self.show()
        self.quitBtn.clicked.connect(self.quitWindow)
        self.threadBtn.clicked.connect(self.stopThread)
        self.refBtn.clicked.connect(self.setReference)
        self.clearBtn.clicked.connect(self.clearReference)
        self.startBtn.clicked.connect(self.startReadout)
        self.sendSPIBtn.clicked.connect(self.getFile)

        self.queueThr = queue.Queue()
        #self.queue = Queue.Queue()
        
        self.frames_el = 0
        self.thread = 0
        self.polling_started = 0
        self.reference_frame = 0
        self.reference_f = 0
        self.frame = 0
        self.setRef = 0

    def getFile(self):
        filePath = QtGui.QFileDialog.getOpenFileName()
        self.getFilenameEdit.setText(filePath[0])
    
    def clearReference(self):
        self.reference_f = 0
        self.setRef = 1

    def setReference(self):
        self.reference_frame = self.frame
        self.reference_f = 1
        self.setRef = 1

    def quitWindow(self):
        if self.thread != 0:
            self.thread.stop() 
            self.thread.join()
        self.close()
   
    def stopThread(self):
        if self.thread != 0:
            self.thread.stop() 
            self.thread.join()

            
    def pollQueue(self):
        #time.sleep(2)
        if not self.queueThr.empty():
            frame = self.queueThr.get()
            self.frame = frame[0]
            if (self.reference_f):
                if(self.setRef):
                    self.imv.setLevels(0,5)
                    self.setRef = 0
                frame_to_display = np.subtract(frame[0],self.reference_frame)
            else:
                if(self.setRef):
                    self.imv.setLevels(0,250)
                    self.setRef = 0
                frame_to_display = frame[0]
            self.imv.setImage(frame_to_display, autoRange=False, autoLevels=False, autoHistogramRange=False)
            #self.imv.setImage(frame[0])           
            #self.outFile.write((str(avgDat) + "\n"))
            self.avgValVect.append(frame[2])
            self.curve.setData(self.avgValVect)
            
            if self.saveBox.isChecked():
                filestr = 'view' + str(frame[1]) + '.png'
                self.exporter.export(filestr)
                filestr = 'line' + str(frame[1]) + '.png'
                self.exporter_line.export(filestr)
                
            #self.plot.hideAxis('bottom')
            #print ("Drawing frame: " + str(self.frames_el))
            self.frameLb.setText(("N = " + str(frame[1])))

        QtCore.QTimer.singleShot(20, self.pollQueue)
            
                   

        #self.window.after(100, self.pollQueue)


    def startReadout(self):
        
        self.thread = ThreadedTask(self.getFilenameEdit.text(), self.queueThr)
        self.thread.start()
        if(not self.polling_started):
            self.polling_started = 1
            self.pollQueue()
            

class ThreadedTask(threading.Thread):
    def __init__(self, infileName, queue):
        threading.Thread.__init__(self)
        self.infile = open(infileName, "r")
        self.queue = queue
        self.counter = 0
        self._stop_event = threading.Event()
    def stop(self):
        #print "Stopping file read"
        self._stop_event.set()
    def stopped(self):
        return self._stop_event.is_set()
    def run(self):  
        tmp = self.infile.readline()
        while tmp:
            #frame_data = np.array([64,200])
            #frame_data = np.genfromtxt(self.infile, delimiter=' ', dtype=None,)
            frame_data = np.reshape(np.fromfile(self.infile,count=12800,sep=" "), (200,64))
            #frame_data = np.fromfile(self.infile,count=12800,sep=" ")
            avg_str = self.infile.readline()
            avgDat = re.findall("\d+\.\d+", avg_str)
            self.queue.put((frame_data,self.counter,float(avgDat[0])))
            self.counter = self.counter + 1 
            tmp = self.infile.readline()
            tmp = self.infile.readline()
        self.infile.close()
        
        
        



def main():

    app = QtGui.QApplication(sys.argv)
    ex = GuiViewer()
    sys.exit(app.exec_())




if __name__ == '__main__':
    main()
