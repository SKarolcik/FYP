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

from matplotlib import cm
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import coloredGraph

FREQUENCY = 2000000


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
        self.imv = coloredGraph.MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix'])
        self.imv.setLevels(0,255)
        
        self.win = pg.GraphicsWindow(title="Average sensor value")
        self.win.resize(1200,50)
        self.avgVal = self.win.addPlot()
        self.curve = self.avgVal.plot()
        self.avgValVect = []
        
        #cm_qt = cmapToColormap(cm.get_cmap("jet"))
        #cm_qt = map(list, zip(*cm_qt))
        #print cm_qt[0]
        #colormap = pg.ColorMap(cm_qt[0],cm_qt[1], 'rgb')
        #self.imv.setColorMap(cmapToColormap(cm.get_cmap("jet")))

        #self.imv = pg.GraphicsWindow()
        #self.plot = self.imv.addPlot()

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

        self.queue = Queue.Queue()
        self.inputFile = open("out_readings.dat", "r")
        self.outFile = open("avg_frames.dat", "w")
        self.thread = 0
        self.SPIhandle = 0

        self.pi = pigpio.pi()             # exit script if no connection
        if not self.pi.connected:
            exit()
        self.pi.hardware_clock(4, FREQUENCY) # 2 KHz clock on GPIO 4


    def quitWindow(self):
        self.pi.hardware_clock(4,0)
        self.pi.stop()
        if self.thread != 0:
            self.thread.stop() 
            self.thread.join()
        self.inputFile.close()
        self.outFile.close()
        self.close()

    def stopThread(self):
        if self.thread != 0:
            self.thread.stop() 
            self.thread.join()

    def resetChip(self):
        if self.SPIhandle != 0 :
            (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, [5, 5])
            self.setSPIEdit.setText("05 05")
            self.receivedSPIEdit.setText((format(rx_data[0], '02X') + " " + format(rx_data[1], '02X')))
            
    def pollQueue(self):
        #time.sleep(2)
        if not self.queue.empty():
            frame = self.queue.get()
            self.imv.setImage(frame[0], autoRange=False, autoLevels=False, autoHistogramRange=False)
            #print np.mean(frame[0].reshape((12800,1)))
            avgDat = np.mean(frame[0].reshape((12800,1)))
            self.avgValVect.append(avgDat)
            self.outFile.write((str(avgDat) + "\n"))
            self.curve.setData(self.avgValVect)
            #im = pg.ImageItem(frame[0], levels=(0x000,0xFFF))
            #self.imv.setLookupTable(self.cmLut)
            #self.plot.addItem(im)
            #self.plot.hideAxis('left')
            #self.plot.hideAxis('bottom')
            print ("Drawing frame: " + str(frame[2]) + ",With values: " + str(frame[0][10][0]))
            self.frameLb.setText(("N = " + str(frame[2])))
            self.timeLb.setText(("t = " + str(frame[1])))

        QtCore.QTimer.singleShot(50, self.pollQueue)
            
                   

        #self.window.after(100, self.pollQueue)


    def sendSPI(self):
        command = self.sendSPIEdit.text()
        self.sendSPIEdit.setText("")
        hex_data = bytearray.fromhex(command)
        self.SPIhandle = self.pi.spi_open(0, 50000, 0b0100000011110000000001) 
        (count, rx_data) = self.pi.spi_xfer(self.SPIhandle, hex_data)
        sentString = format(hex_data[0], '02X') + " " + format(hex_data[1], '02X')
        recString = format(rx_data[0], '02X') + " " + format(rx_data[1], '02X')
        self.setSPIEdit.setText(sentString)
        self.receivedSPIEdit.setText(recString)
        if (hex_data[0] >= 0x80):
            self.thread = ThreadedTask(self.inputFile, self.queue, hex_data[1])
            self.thread.start()
            #time.sleep(0.5)
            self.pollQueue()
            #print "Started frame"
        


class ThreadedTask(threading.Thread):
    def __init__(self, inputFile, queue, increments):
        threading.Thread.__init__(self)
        self.inputFile = inputFile
        self.queue = queue
        self._stop_event = threading.Event()
        self.counter = 0
        self.increments = (1.0/(float(FREQUENCY)/float(increments))) * 12800
    def stop(self):
        print "Stopping data read"
        self._stop_event.set()
    def stopped(self):
        return self._stop_event.is_set()
    def run(self):   
        while not self.stopped():
            try:
                time.sleep(0.1)  # Simulate long running process
                frameFlattened = np.zeros((12800,1))
                for i in range(6400):
                    pos = i*2
                    val1 = self.inputFile.readline()
                    if val1 == '':
                        time.sleep(1)
                        val1 = self.inputFile.readline()
                        if val1 == '':
                            print ("Problem at: " + str(i))
                            print "Stopping data read"
                            self._stop_event.set()
                    
                    val1 = int(val1)
                    val0 = val1 & 0xFFF
                    val1 = val1 >> 16
                    i0 = ((2.0 - (val0/4095.0)*2.5)/8.0)*1000
                    i1 = ((2.0 - (val1/4095.0)*2.5)/8.0)*1000
                    frameFlattened[pos] = i0
                    frameFlattened[pos+1] = i1
                print ("Prepared frame: " + str(self.counter) + ",With value: " +str(frameFlattened[100]))
                singleFrame = np.transpose(frameFlattened.reshape((64,200)))           
                #print "frame happened" + str(single_frame[1][1]) + " And seconds currently: " + str(seconds_elapsed)
                self.queue.put((singleFrame,(self.counter*self.increments),self.counter))
                self.counter = self.counter + 1
                #self.queue.put(self.singleFrame)
            except:
                self.inputFile.close()
                self.inputFile = open("out_readings.dat", "r")


def main():

    app = QtGui.QApplication(sys.argv)
    ex = GuiViewer()
    sys.exit(app.exec_())




if __name__ == '__main__':
    main()
