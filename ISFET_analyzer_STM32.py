#!/usr/bin/env python
__author__ = 'Stefan'
import sys
import os
import numpy as np
import pigpio

import threading
import Queue
import time
import collections
import struct

from matplotlib import cm
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg

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


        self.sendSPIBtn = QtGui.QPushButton("Send SPI")
        self.quitBtn = QtGui.QPushButton("Quit")
        self.resetBtn = QtGui.QPushButton("Reset chip")
        self.threadBtn = QtGui.QPushButton("Stop thread")
        self.sendSPIEdit = QtGui.QLineEdit(self)

        self.setSPIEdit = QtGui.QLineEdit(self)
        self.setSPIEdit.setReadOnly(True)
        self.setSPILb = QtGui.QLabel('Sent SPI')
        self.receivedSPIEdit = QtGui.QLineEdit(self)
        self.receivedSPIEdit.setReadOnly(True)
        self.receivedSPILb = QtGui.QLabel('Received SPI')

        self.frameLb = QtGui.QLabel('N = N/A')
        self.timeLb = QtGui.QLabel('t = N/A')

        #self.imv = pg.ImageView()
        self.imv = MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix'])
        self.imv.setLevels(0,250)
        
        self.win = pg.GraphicsWindow(title="Average sensor value")
        self.win.resize(1200,50)
        self.avgVal = self.win.addPlot()
        self.curve = self.avgVal.plot()
        self.avgValVect = []
        
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.sendSPIBtn, 1, 0)
        grid.addWidget(self.sendSPIEdit, 1, 1)
        grid.addWidget(self.quitBtn, 1, 3)
        grid.addWidget(self.setSPILb, 2, 0)
        grid.addWidget(self.setSPIEdit, 2, 1)
        grid.addWidget(self.resetBtn, 1, 2)
        grid.addWidget(self.threadBtn, 2, 2)
        grid.addWidget(self.receivedSPILb, 3, 0)
        grid.addWidget(self.receivedSPIEdit, 3, 1)
        grid.addWidget(self.frameLb, 4, 2)
        grid.addWidget(self.timeLb, 4, 3)

        grid.addWidget(self.imv, 5, 0, 4, 4)
        
        grid.addWidget(self.win, 10, 0, 4, 4)
        

        self.setLayout(grid)

        self.setGeometry(200, 200, 1200, 800)
        self.setWindowTitle('ISFET viewer')    
        self.show()
        self.sendSPIBtn.clicked.connect(self.sendSPI)
        self.quitBtn.clicked.connect(self.quitWindow)
        self.resetBtn.clicked.connect(self.resetChip)
        self.threadBtn.clicked.connect(self.stopThread)

        self.pi = pigpio.pi()             # exit script if no connection
        if not self.pi.connected:
            exit()
        self.pi.hardware_clock(4, FREQUENCY) # 2 KHz clock on GPIO 4
        
        self.queue = Queue.Queue()
        self.thread_queue = Queue.Queue()
        self.outFile = open("isfet_frames.dat", "w")
        self.SPIhandle = self.pi.spi_open(0, 500000, 0b0100000011110000000001) 
        self.SPIhandle_STM32 = self.pi.spi_open(1, 5000000, 0b0100000011110000000001) 
        self.pi.set_mode(27,pigpio.INPUT)
        self.pi.set_mode(14,pigpio.OUTPUT)
        self.cb = self.pi.callback(27, pigpio.RISING_EDGE, self.isr_frame)
        self.hex_data = [0,0]
        self.time_el = 0.0
        self.frames_el = 0
        self.thread = ThreadedTask(self.outFile, self.thread_queue)
        self.start_time = time.time()
        self.thread.start()




    def quitWindow(self):
        self.pi.hardware_clock(4,0)
        self.pi.stop()
        if self.thread != 0:
            self.thread.stop() 
            self.thread.join()
        self.outFile.close()
        self.close()

    def isr_frame (self, gpio, level, tick):
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, [0, 0])
        self.pi.write(14,1)
        byte_frame = self.pi.spi_read(self.SPIhandle_STM32, 25600)
        int_values = list(byte_frame[1])
        frame_values = [(int_values[i]*256+int_values[i+1]) for i in xrange(0, len(int_values), 2)]
        frame_conv = map(lambda x : ((2.0 - (x/4095.0)*2.5)/8.0)*1000, frame_values)
        frame = np.transpose(np.array(frame_conv).reshape((64,200)))
        avgDat = np.mean(np.array(frame_conv))
        self.avgValVect.append(avgDat)
        #self.curve.setData(self.avgValVect)
        self.pi.write(14,1)
        #self.draw_frame(frame)
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, self.hex_data)
        #print "Interrupt happened\n"
        self.frames_el += 1
        self.time_el = time.time() - self.start_time
        self.thread_queue.put((self.frames_el, frame, avgVal))
        self.queue.put((frame,self.frames_el, self.time_el, self.avgValVect))
   
    def stopThread(self):
        if self.thread != 0:
            self.thread.stop() 
            self.thread.join()

    def resetChip(self): 
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, [5, 5])
        self.setSPIEdit.setText("05 05")
        self.receivedSPIEdit.setText((format(rx_data[0], '02X') + " " + format(rx_data[1], '02X')))
            
    def pollQueue(self):
        #time.sleep(2)
        if not self.queue.empty():
            frame = self.queue.get()
            self.imv.setImage(frame[0], autoRange=False, autoLevels=False, autoHistogramRange=False)
            #self.outFile.write((str(avgDat) + "\n"))
            self.curve.setData(frame[3])
            #self.plot.hideAxis('bottom')
            #print ("Drawing frame: " + str(self.frames_el))
            time_in_s = "%.4f"% frame[2]
            self.frameLb.setText(("N = " + str(frame[1])))
            self.timeLb.setText(("t = " + time_in_s + "s"))

        QtCore.QTimer.singleShot(50, self.pollQueue)
            
                   

        #self.window.after(100, self.pollQueue)


    def sendSPI(self):
        command = self.sendSPIEdit.text()
        self.sendSPIEdit.setText("")
        self.hex_data = bytearray.fromhex(command)
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, self.hex_data)
        sentString = format(self.hex_data[0], '02X') + " " + format(self.hex_data[1], '02X')
        recString = format(rx_data[0], '02X') + " " + format(rx_data[1], '02X')
        self.setSPIEdit.setText(sentString)
        self.receivedSPIEdit.setText(recString)
        #print str(self.SPIhandle)
        self.time_el = 0
        self.frames_el = 0
        self.avgValVect = []
        #self.frames_el += 1
        #self.time_el = self.time_el + (1.0/2000000.0)*(self.hex_data[1])*12800.0
        #print str(self.hex_data[1])
        #print self.frames_el
        #print self.time_el
        #if not self.queue.empty():
            #print self.queue.get()
        if (self.hex_data[0] >= 0x80):
            #self.thread = ThreadedTask(self.inputFile, self.queue, hex_data[1])
            #self.thread.start()
            #time.sleep(0.5)
            self.start_time = time.time()
            self.pollQueue()
            #print "Started frame"

class ThreadedTask(threading.Thread):
    def __init__(self, outFile, queue):
        threading.Thread.__init__(self)
        self.outFile = outFile
        self.queue = queue
        self._stop_event = threading.Event()
    def stop(self):
        print "Stopping writing to file"
        self._stop_event.set()
    def stopped(self):
        return self._stop_event.is_set()
    def run(self):   
        while not self.stopped():
            if not self.queue.empty():
                frame_struct = self.queue.get()
                self.outFile.write("Frame no: " + str(frame_struct[0]) + "\n")
                np.savetxt(self.outFile, frame_struct[1], fmt='%.4f', delimiter=' ', newline='\n')
                self.outFile.write("Average values of frame: " + str(frame_struct[2]) + "\n\n")




def main():

    app = QtGui.QApplication(sys.argv)
    ex = GuiViewer()
    sys.exit(app.exec_())




if __name__ == '__main__':
    main()
