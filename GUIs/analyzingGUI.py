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


        self.btn1 = QtGui.QPushButton("Open file")
        self.btn2 = QtGui.QPushButton("...")
        self.btn3 = QtGui.QPushButton("Next frame")
        self.btn4 = QtGui.QPushButton("Close file")
        self.btn5 = QtGui.QPushButton("Last frame")
        

        self.fileP = QtGui.QLineEdit(self)
        self.frameLb = QtGui.QLabel('N = N/A')
        

        #self.imv = pg.ImageView()
        self.imv = coloredGraph.MplCmapImageView(additionalCmaps=['jet', 'viridis', 'seismic', 'cubehelix'])
        self.imv.setLevels(0,255)
     
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.fileP, 1, 0, 1, 2)
        grid.addWidget(self.btn2, 1, 2)
        grid.addWidget(self.btn1, 2, 1)
        grid.addWidget(self.btn3, 3, 1)
        grid.addWidget(self.btn5, 3, 2)
        grid.addWidget(self.btn4, 2, 2)
        grid.addWidget(self.frameLb, 3, 3)

        grid.addWidget(self.imv, 5, 0, 4, 4)
        

        self.setLayout(grid)

        self.setGeometry(200, 200, 1200, 800)
        self.setWindowTitle('ISFET analyzer')    
        self.show()
        self.btn1.clicked.connect(self.btn1Pres)
        self.btn2.clicked.connect(self.btn2Pres)
        self.btn3.clicked.connect(self.btn3Pres)
        self.btn4.clicked.connect(self.btn4Pres)
        self.btn5.clicked.connect(self.btn5Pres)

        
        self.inputFile = 0
        
        self.frameCounter = 0
        self.frames = []
    
    def btn1Pres(self):
    	name = self.fileP.text()
    	self.inputFile = open(name, 'r')
    	self.frameCounter = 0    
    def btn2Pres(self):
        filePath = QtGui.QFileDialog.getOpenFileName()
        self.fileP.setText(filePath[0])
        
    def btn5Pres(self):
        self.frameCounter = self.frameCounter - 1
        self.imv.setImage(self.frames[self.frameCounter], autoRange=False, autoLevels=False, autoHistogramRange=False)
    	self.frameLb.setText(str(self.frameCounter))
    
    def btn3Pres(self):
    	
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
            #print ("Prepared frame: " + str(self.counter) + ",With value: " +str(frameFlattened[100]))
        singleFrame = np.transpose(frameFlattened.reshape((64,200))) 
    
    	self.imv.setImage(singleFrame, autoRange=False, autoLevels=False, autoHistogramRange=False)
    	self.frameLb.setText(str(self.frameCounter))
   	self.frameCounter = self.frameCounter + 1
    	self.frames.append(singleFrame)
    
    def btn4Pres(self):
        self.inputFile.close()



def main():

    app = QtGui.QApplication(sys.argv)
    ex = GuiViewer()
    sys.exit(app.exec_())




if __name__ == '__main__':
    main()

