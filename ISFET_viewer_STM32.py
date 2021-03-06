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

#avconv -f x11grab -r 25 -s 1920x1080 -i :0.0+0,0 -vcodec libx264 video.mkv

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
        self.startBtn = QtGui.QPushButton("Start CM array readout")
        self.startPGBtn = QtGui.QPushButton("Start CM-PG array readout")
        self.startBtn.setStyleSheet("color: #013220")
        self.startPGBtn.setStyleSheet("color: #013220")
        self.refBtn = QtGui.QPushButton("Set reference")
        self.refPGBtn = QtGui.QPushButton("Set PG reference")
        self.clearBtn = QtGui.QPushButton("Clear reference")
        self.clearPGBtn = QtGui.QPushButton("Clear PG reference")
        self.sendSPIEdit = QtGui.QLineEdit(self)
        self.saveToFile = QtGui.QCheckBox("Save to file?")

        self.setSPIEdit = QtGui.QLineEdit(self)
        self.setSPIEdit.setReadOnly(True)
        self.setSPILb = QtGui.QLabel('Sent SPI')
        self.receivedSPIEdit = QtGui.QLineEdit(self)
        self.receivedSPIEdit.setReadOnly(True)
        self.receivedSPILb = QtGui.QLabel('Received SPI')
        self.logo = QtGui.QLabel(self)
        pixmap = QtGui.QPixmap('logo_with_desc.png')
        self.logo.setPixmap(pixmap.scaled(501,200,QtCore.Qt.KeepAspectRatio))

        self.frameLb = QtGui.QLabel('N = N/A')
        self.timeLb = QtGui.QLabel('t = N/A')

        #self.imv = pg.ImageView()
        self.imv = MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix'], view=pg.PlotItem())
        self.imv.setLevels(0,250)
        tmp_frame = np.transpose(np.zeros((64,200)))
        self.imv.setImage(tmp_frame, autoRange=False, autoLevels=False, autoHistogramRange=False)

        
        self.win = pg.GraphicsWindow(title="Average frame value")
        self.win.resize(1200,50)
        self.avgVal = self.win.addPlot()
        self.curve = self.avgVal.plot()
        self.avgValVect = []
        
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.logo, 1, 0, 4, 1)
        grid.addWidget(self.startBtn, 1, 1, 1, 2)
        grid.addWidget(self.sendSPIBtn, 2, 1)
        grid.addWidget(self.sendSPIEdit, 2, 2)
        grid.addWidget(self.quitBtn, 1, 4)
        grid.addWidget(self.setSPILb, 3, 1)
        grid.addWidget(self.setSPIEdit, 3, 2)
        grid.addWidget(self.resetBtn, 1, 3)
        grid.addWidget(self.refBtn, 2, 3)
        grid.addWidget(self.clearBtn, 2, 4)
        grid.addWidget(self.receivedSPILb, 4, 1)
        grid.addWidget(self.receivedSPIEdit, 4, 2)
        grid.addWidget(self.startPGBtn, 5, 1, 1, 2)
        grid.addWidget(self.refPGBtn, 5, 3)
        grid.addWidget(self.clearPGBtn, 5, 4)
        grid.addWidget(self.saveToFile, 6, 2)
        grid.addWidget(self.frameLb, 6, 3)
        grid.addWidget(self.timeLb, 6, 4)

        grid.addWidget(self.imv, 7, 0, 4, 5)
        
        grid.addWidget(self.win, 12, 0, 4, 5)
        

        self.setLayout(grid)

        self.setGeometry(250, 100, 1200, 900)
        self.setWindowTitle('ISFET viewer')    
        self.show()
        self.sendSPIBtn.clicked.connect(self.sendSPI)
        self.quitBtn.clicked.connect(self.quitWindow)
        self.resetBtn.clicked.connect(self.resetChip)
        self.refBtn.clicked.connect(self.setReference)
        self.clearBtn.clicked.connect(self.clearReference)
        self.refPGBtn.clicked.connect(self.calculatePGReference)
        self.clearPGBtn.clicked.connect(self.clearPGReference)
        self.startBtn.clicked.connect(self.startReadout)
        self.startPGBtn.clicked.connect(self.startPGReadout)

        self.pi = pigpio.pi()             # exit script if no connection
        if not self.pi.connected:
            exit()
        self.pi.hardware_clock(4, FREQUENCY) # 2 KHz clock on GPIO 4
        
        self.queue = Queue.Queue()
        self.thread_queue = Queue.Queue()
        self.SPIhandle = self.pi.spi_open(0, 500000, 0b0100000011110000000001) 
        self.SPIhandle_STM32 = self.pi.spi_open(1, 8000000, 0b0100000011110000000001) 
        self.pi.set_mode(27,pigpio.INPUT)
        self.pi.set_mode(14,pigpio.OUTPUT)
        self.cb = self.pi.callback(27, pigpio.RISING_EDGE, self.isr_frame)
        self.hex_data = [0,0]
        self.time_el = 0.0
        self.frames_el = 0
        self.start_time = time.time()
        self.polling_started = 0
        self.pi.write(14,1)
        time.sleep(0.5)
        self.pi.write(14,0)
        self.reference_frame = 0
        self.reference_f = 0
        self.frame = 0
        self.setRef = 0

        self.received_frame = 0
        self.PG_f = 0
        self.PG_DAC_data = [0x00, 0x00]*12800
        #self.thread.start()

    def startReadout(self):
        self.hex_data = [0x80, 0x12]
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, self.hex_data)
        sentString = format(self.hex_data[0], '02X') + " " + format(self.hex_data[1], '02X')
        recString = format(rx_data[0], '02X') + " " + format(rx_data[1], '02X')
        self.setSPIEdit.setText(sentString)
        self.receivedSPIEdit.setText(recString)
        self.startBtn.setEnabled(False)
        
        self.start_time = time.time()
        if(not self.polling_started):
            self.polling_started = 1
            self.pollQueue()
    
    def startPGReadout(self):
        self.hex_data = [0x90, 0x12]
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, self.hex_data)
        sentString = format(self.hex_data[0], '02X') + " " + format(self.hex_data[1], '02X')
        recString = format(rx_data[0], '02X') + " " + format(rx_data[1], '02X')
        self.setSPIEdit.setText(sentString)
        self.receivedSPIEdit.setText(recString)
        self.startPGBtn.setEnabled(False)
        
        self.start_time = time.time()
        if(not self.polling_started):
            self.polling_started = 1
            self.pollQueue()

    def clearReference(self):
        self.reference_f = 0
        self.setRef = 1

    def setReference(self):
        self.reference_frame = self.frame
        self.reference_f = 1
        self.setRef = 1

    def calculatePGReference(self):
        #PG_initial_frame = np.transpose(self.frame).flatten('C')
        PG_initial_frame = self.received_frame
        condition = (PG_initial_frame>=40) & (PG_initial_frame<=180)
        active_pixels = np.extract(condition, PG_initial_frame)
        mean_current = np.mean(active_pixels)
        #print "Mean current is:" + str(mean_current)
        #print "16/187 consfilct pixel is: " + str(PG_initial_frame[3387])
        #print "16/189 normal pixel is: " + str(PG_initial_frame[3389])
        for pixel in range (12800):
            pixel_analyzed = PG_initial_frame[pixel]
            if 50 <= pixel_analyzed <= 180 :
                dI = pixel_analyzed - mean_current
                Vpg = 1.643 - (dI/30)
                DACval = int(4095/(3.286/Vpg))
                if 0 <= DACval <= 4095:
                    (top_byte, bottom_byte) = divmod(DACval,256)
                    self.PG_DAC_data[pixel*2] = top_byte 
                    self.PG_DAC_data[pixel*2+1] = bottom_byte
                #else:
                #    self.PG_DAC_data[pixel*2] = 0x0F
                #    self.PG_DAC_data[pixel*2+1] = 0xFF
                elif DACval < 0:
                    self.PG_DAC_data[pixel*2] = 0x00
                    self.PG_DAC_data[pixel*2+1] = 0x00
                elif DACval > 4095:
                    self.PG_DAC_data[pixel*2] = 0x0F
                    self.PG_DAC_data[pixel*2+1] = 0xFF
            else:
                self.PG_DAC_data[pixel*2] = 0x07
                self.PG_DAC_data[pixel*2+1] = 0xFF
        #self.PG_DAC_data = list(reversed(self.PG_DAC_data))
        self.PG_f = 1
        #outfilePG = open("DAC_setup.txt", "w")
        #np.savetxt(outfilePG, self.PG_DAC_data, fmt='%d', delimiter=' ', newline=' ')
        print "PG reference set!\n"
        # for i, j in enumerate(self.PG_DAC_data):
        #     if j ==0:
        #         print (i)
        # print self.PG_DAC_data[0]
        # print self.PG_DAC_data[-1]
        #print ("PG frame: " + str(PG_initial_frame[0]) + " " + str(PG_initial_frame[1]) + " " + str(PG_initial_frame[2]) + " " + str(PG_initial_frame[3]) + " " + str(PG_initial_frame[4]))    

        #self.PG_f = 1

    def clearPGReference(self):
        self.PG_f = 0

    def quitWindow(self):
        self.pi.hardware_clock(4,0)
        self.pi.stop()
        self.close()

    def isr_frame (self, gpio, level, tick):
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, [0, 0])
        self.pi.write(14,1)
        if (self.PG_f):
            (count, byte_frame) = self.pi.spi_xfer(self.SPIhandle_STM32, self.PG_DAC_data)
        else:
            (count, byte_frame) = self.pi.spi_xfer(self.SPIhandle_STM32, [0x00,0x00]*12800)
        int_values = list(byte_frame)
        frame_values = [(int_values[i]*256+int_values[i+1]) for i in xrange(0, len(int_values), 2)]
        frame_conv = np.array(map(lambda x : ((2.0 - (x/4095.0)*3.25)/8.0)*1000, frame_values))
        self.received_frame = frame_conv
        #print ("Real frame: " + str(frame_conv[0]) + " " + str(frame_conv[1]) + " " + str(frame_conv[2]) + " " + str(frame_conv[3]) + " " + str(frame_conv[4]))
        self.frame = np.transpose(frame_conv.reshape((64,200)))
        #print self.frame[120][1]
        avgDat = np.mean(frame_conv)
        #condition = (frame_conv>=60) & (frame_conv<=180)
        #reduced = np.extract(condition, frame_conv)
        #if reduced.size == 0:
        #    avgDat = 0
        #else:
        #    avgDat = np.mean(reduced)
        if (self.frames_el > 0):
            self.avgValVect.append(avgDat)
        #self.curve.setData(self.avgValVect)
        self.pi.write(14,0)
        #self.draw_frame(frame)
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, self.hex_data)
        #print "Interrupt happened\n"
        self.frames_el += 1
        self.time_el = time.time() - self.start_time
        self.queue.put((self.frame,self.frames_el, self.time_el, self.avgValVect))

    def resetChip(self): 
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, [0, 0])
        self.setSPIEdit.setText("00 00")
        self.receivedSPIEdit.setText((format(rx_data[0], '02X') + " " + format(rx_data[1], '02X')))
        self.time_el = 0
        self.frames_el = 0
        self.avgValVect = []
        self.startBtn.setEnabled(True)
        self.startPGBtn.setEnabled(True)
            
    def pollQueue(self):
        if not self.queue.empty():
            frame = self.queue.get()
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
            self.curve.setData(frame[3])
            time_in_s = "%.4f"% frame[2]
            self.frameLb.setText(("N = " + str(frame[1])))
            self.timeLb.setText(("t = " + time_in_s + "s"))

        QtCore.QTimer.singleShot(30, self.pollQueue)

    def sendSPI(self):
        command = self.sendSPIEdit.text()
        self.sendSPIEdit.setText("")
        self.hex_data = bytearray.fromhex(command)
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, self.hex_data)
        sentString = format(self.hex_data[0], '02X') + " " + format(self.hex_data[1], '02X')
        recString = format(rx_data[0], '02X') + " " + format(rx_data[1], '02X')
        self.setSPIEdit.setText(sentString)
        self.receivedSPIEdit.setText(recString)
        
        #Start of acquisition
        if (self.hex_data[0] >= 0x80):
            self.start_time = time.time()
            if(not self.polling_started):
                self.polling_started = 1
                self.pollQueue()


def main():

    app = QtGui.QApplication(sys.argv)
    ex = GuiViewer()
    sys.exit(app.exec_())




if __name__ == '__main__':
    main()
