__author__ = 'Stefan'
import matplotlib
matplotlib.use('TkAgg')
import numpy as np
import pigpio
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
        self.close_button = Button(window, text="Quit", command=self.exitWindow)
        self.sendSPIbutton = Button(window,text="Send through SPI", command=self.sendSPI)
        self.readSPIlabel = Label(window, text="Received from SPI:")
        self.readSPIvalue = Label(window, text="N/A")
        self.terminalView = Frame(window, heigh=100,width=300)
        
        self.close_button.grid(row=2,column=4)
        self.box.grid(row=2,column=3)
        self.readSPIlabel.grid(row=3,column=2)
        self.readSPIvalue.grid(row=3,column=3)
        self.sendSPIbutton.grid(row=2,column=2)
        self.terminalView.grid(row=6,column=2,columnspan=3)

        self.pi = pigpio.pi()             # exit script if no connection
        if not self.pi.connected:
            exit()
        self.pi.hardware_clock(4, 1000000) # 5 KHz clock on GPIO 4


    def exitWindow(self):
        self.pi.hardware_clock(4,0)
        self.pi.stop()
        self.window.quit()
        
    def plot (self):
    
        fig = Figure(figsize=(4,4))
        a = fig.add_subplot(111)
        a.imshow(heat_map, cmap='hot', interpolation='nearest')

        a.set_title ("Estimation Grid", fontsize=16)
        a.set_ylabel("Y", fontsize=14)
        a.set_xlabel("X", fontsize=14)
        
        canvas = FigureCanvasTkAgg(fig, master=self.window)
        canvas.get_tk_widget().grid(row=5,column=2,columnspan=3)
        canvas.draw()

    def sendSPI(self):
        hex_vals = self.box.get()
        self.box.delete(0,END)
        print "Nothing " + hex_vals
        hex_data = bytearray.fromhex(hex_vals)
        h = self.pi.spi_open(0, 50000, 0b0100000011110000000001) 
        (count, rx_data) = self.pi.spi_xfer(h, hex_data)
        print count
        print rx_data[0]
        self.readSPIvalue["text"] = str(hex(rx_data[0])) + " " + str(hex(rx_data[1]))
        if (hex_data[1] == 0x80):
            self.plot()
            



window= Tk()
start= mclass (window)
window.mainloop()
