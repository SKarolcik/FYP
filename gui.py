__author__ = 'Stefan'
import matplotlib
matplotlib.use('TkAgg')
import numpy as np
import pigpio
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from Tkinter import *
import os

import threading
import Queue


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

    def exitWindow(self):
        #self.pi.hardware_clock(4,0)
        #self.pi.stop()
        
        self.thread.stop()
       #self.plotting.stop()
        #self.thread.join()  
        #self.plotting.join() 
        os.close(self.device) 
        self.window.quit()
        
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
            

class ThreadedPlot(threading.Thread):
    def __init__(self, window, queue):
        threading.Thread.__init__(self)
        self.window = window
        self.queue = queue
        self._stop_event = threading.Event()
    def stop(self):
        print "Stopping plot"
        self._stop_event.set()
    def stopped(self):
        return self._stop_event.is_set()
    def run(self):
        #time.sleep(5)  # Simulate long running process
        currFrame = self.queue.get()
        fig = Figure(figsize=(6,2))
        
        while not self.stopped():
            if (not self.queue.empty()):
                print "Plotting"
                fig.clf()
                a = fig.add_subplot(111)
                a.imshow(currFrame, cmap='hot', interpolation='nearest',vmin=0,vmax=0xFFF)
                #a.plot(p, range(2 +max(x)),color='blue')
                #a.invert_yaxis()

                a.set_title ("Estimation Grid", fontsize=16)
                a.set_ylabel("Y", fontsize=14)
                a.set_xlabel("X", fontsize=14)
                
                canvas = FigureCanvasTkAgg(fig, master=self.window)
                #canvas = prepHeatMap(heat_map)
                canvas.get_tk_widget().grid(row=4,column=2,columnspan=6)
                #canvas.pack()
                canvas.draw()

'''
class ThreadedTask(threading.Thread):
    def __init__(self, window, device):
        threading.Thread.__init__(self)
        self.window = window
        self.device = device
        self.frame = np.zeros((64,200))
        self._stop_event = threading.Event()
        self.figure = Figure(figsize=(6,2))
    def stop(self):
        print "Stopping data read"
        self._stop_event.set()
    def stopped(self):
        return self._stop_event.is_set()
    def run(self):
        #time.sleep(5)  # Simulate long running process
        while not self.stopped():
            single_frame = self.frame
            #print "Doing stuff"
            for x in range(200):
                for y in range(64):
                    value = os.read(self.device,3)
                    if value == '':
                        value = "0"
                    single_frame[y][x] = int(value)
                    #print single_frame[y][x]
            print "frame"
            #self.queue.put(single_frame)
            self.figure.clf()
            a = self.figure.add_subplot(111)
            a.imshow(single_frame, cmap='hot', interpolation='nearest',vmin=0,vmax=0xFFF)

            a.set_title ("Estimation Grid", fontsize=16)
            a.set_ylabel("Y", fontsize=14)
            a.set_xlabel("X", fontsize=14)
                
            canvas = FigureCanvasTkAgg(self.figure, master=self.window)
            canvas.get_tk_widget().grid(row=4,column=2,columnspan=6)
            canvas.draw()

window= Tk()
start= mclass (window)
window.mainloop()
