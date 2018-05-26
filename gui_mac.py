__author__ = 'Stefan'
import matplotlib
matplotlib.use('TkAgg')
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from Tkinter import *
import os
import time

import threading
import Queue

FREQUENCY = 2000000


class mclass:
    def __init__(self,  window):
        self.window = window
        self.box = Entry(window)
        self.close_button = Button(window, text="Quit", command=self.exitWindow)
        self.sendSPIbutton = Button(window,text="Send through SPI", command=self.sendSPI)
        self.readSPIlabel = Label(window, text="Received from SPI:")
        self.readSPIvalue = Label(window, text="N/A")
        self.queue = Queue.Queue()
        
        self.close_button.grid(row=2,column=4)
        self.box.grid(row=2,column=3)
        self.readSPIlabel.grid(row=3,column=2)
        self.readSPIvalue.grid(row=3,column=3)
        self.sendSPIbutton.grid(row=2,column=2)

        self.figure = Figure(figsize=(12,4))

        self.inputFile = open("adc_data.dat", "r")
        


    def exitWindow(self):
        
        
        self.thread.stop() 
        self.thread.join()
        self.inputFile.close()               
        self.window.quit()

    def pollQueue(self):
        if not self.queue.empty():
            frame = self.queue.get()
            #print frame
            
            self.figure.clf()
            a = self.figure.add_subplot(111)
            a.imshow(frame[0], cmap='hot', interpolation='nearest',vmin=0,vmax=0xFFF)

            a.set_title (("N = " + str(frame[2]) + " Frame at t = " + str(frame[1]) + "s"), fontsize=16)
            a.set_ylabel("Y", fontsize=14)
            a.set_xlabel("X", fontsize=14)
                
            canvas = FigureCanvasTkAgg(self.figure, master=self.window)
            canvas.get_tk_widget().grid(row=4,column=2,columnspan=10)
            canvas.draw()         

        self.window.after(100, self.pollQueue)


    def sendSPI(self):
        
        increment = 0xA
        self.thread = ThreadedTask(self.inputFile, self.queue, increment)
        self.thread.start()
        time.sleep(1)
        self.pollQueue()
        
        
        
        #while not self.queue.empty():
        #    print self.queue.get()
        #    print "Got frame"
            

        #self.plot(heat_map)
class ThreadedTask(threading.Thread):
    def __init__(self, inputFile, queue, increments):
        threading.Thread.__init__(self)
        self.inputFile = inputFile
        self.queue = queue
        self._stop_event = threading.Event()
        self.counter = 0
        self.increments = float(FREQUENCY)/float(increments)
    def stop(self):
        print "Stopping data read"
        self._stop_event.set()
    def stopped(self):
        return self._stop_event.is_set()
    def run(self):   
        while not self.stopped():
            time.sleep(2)  # Simulate long running process
            frameFlattened = np.zeros((12800,1))
            for i in range(6400):
                pos = i*2
                val1 = self.inputFile.readline()
                if not val1:
                    break
                val1 = int(val1)
                val0 = val1 & 0xFFF
                val1 = val1 >> 16
                frameFlattened[pos] = val0
                frameFlattened[pos+1] = val1
            single_frame = frameFlattened.reshape((64,200))
            seconds_elapsed = 1/self.increments * self.counter * 12800
            
            #print "frame happened" + str(single_frame[1][1]) + " And seconds currently: " + str(seconds_elapsed)
            self.queue.put((single_frame,seconds_elapsed,self.counter))
            self.counter = self.counter + 1
            #self.queue.put(single_frame)
            #

window= Tk()
start= mclass (window)
window.mainloop()
