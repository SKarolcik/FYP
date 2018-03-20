__author__ = 'Stefan'
import matplotlib
matplotlib.use('TkAgg')
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from Tkinter import *
import os

heat_map = [[2, 50, 100, 150, 200],
            [300, 400, 500, 600, 700],
            [1000, 1500, 2000, 2500, 3000],
            [3200, 0x3FE, 3400, 3600, 3800],
            [4000, 21, 22, 23, 0x2FF]]

class mclass:
    def __init__(self,  window):
        self.window = window
        self.box = Entry(window)
        self.close_button = Button(window, text="Quit", command=window.quit)
        self.sendSPIbutton = Button(window,text="Send through SPI", command=self.sendSPI)
        self.readSPIlabel = Label(window, text="Received from SPI:")
        self.readSPIvalue = Label(window, text="N/A")
        self.terminalView = Frame(window, heigh=100,width=300)
        
        self.checkbutton = Button (window, text="Check", command=self.plot)
        self.close_button.grid(row=2,column=4)
        self.box.grid(row=2,column=3)
        self.readSPIlabel.grid(row=3,column=2)
        self.readSPIvalue.grid(row=3,column=3)
        self.sendSPIbutton.grid(row=2,column=2)
        self.checkbutton.grid(row=4,column=2)
        self.terminalView.grid(row=6,column=2,columnspan=3)

        self.pi = pigpio.pi()             # exit script if no connection
        if not self.pi.connected:
            exit()
        self.pi.hardware_clock(4, 1000000) # 5 KHz clock on GPIO 4



    def plot (self):
        #x=np.array ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        #v= np.array ([16,16.31925,17.6394,16.003,17.2861,17.3131,19.1259,18.9694,22.0003,22.81226])
        #p= np.array ([16.23697,     17.31653,     17.22094,     17.68631,     17.73641 ,    18.6368,
        #    19.32125,     19.31756 ,    21.20247  ,   22.41444   ,  22.11718  ,   22.12453])
    
        fig = Figure(figsize=(4,4))
        a = fig.add_subplot(111)
        a.imshow(heat_map, cmap='hot', interpolation='nearest')
        #a.plot(p, range(2 +max(x)),color='blue')
        #a.invert_yaxis()

        a.set_title ("Estimation Grid", fontsize=16)
        a.set_ylabel("Y", fontsize=14)
        a.set_xlabel("X", fontsize=14)
        
        canvas = FigureCanvasTkAgg(fig, master=self.window)
        #canvas = prepHeatMap(heat_map)
        canvas.get_tk_widget().grid(row=5,column=2,columnspan=3)
        #canvas.pack()
        canvas.draw()

    def sendSPI(self):
        print "Nothing " + self.box.get()
        h = self.pi.spi_open(1, 50000, 3) 
        (count, rx_data) = pi.spi_xfer(h, b'\x01\x80\x00')
        self.readSPIvalue["text"] = self.box.get()



window= Tk()
start= mclass (window)
window.mainloop()