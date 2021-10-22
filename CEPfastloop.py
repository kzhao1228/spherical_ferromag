#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
CEP fastloop wedgemover feedback
reads AOM voltage and moves intracavity wedge to adjust AOM voltage to setpoint.
This keeps the fast loop CEP lock in a stable condition over the whole workday.
The AOM voltage range is 0 to 1V, best lock is usually in the middle 400 to 600mV.

The AOM voltage in range is read via Adafruit ADS1015 12 bit ADC
Feedback is applied if locking voltage goes outside user defined range.

This version talks to a new focus picomotor driver via serial port and
drives a single picomotor actuator connected to a translation stage
moving one of the two dispersion control wedges inside the Femtopower oscillator.

A future version might use an analog output via Adafruit MCP4725 DAC to Susan's DIY piezodriver.


author: Tobias Witting
version history:
2016-03-12: TW created this
2016-03-13: TW minor cleanup and added logging to file
"""

import sys
from PyQt4 import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import time
from adafruit_ads1x15 import ads1x15
import serial

class CEPfastloop(QtGui.QWidget):
    
    def __init__(self):
        super(CEPfastloop, self).__init__()
        self.initUI()

        
    def initUI(self):
        self.ADC_Nsamples      = 50
        self.hist_length       = 500
        self.testing           = 0    # if 1 testing with fake data and fake wedge, =0 read ADS1015 and talk to picomotor over serial
        self.feedbackactive    = 0
        self.feedbackstepsize  = 20   # bigger = more distrubance to oscillator but faster convergence of feedback 10 to 20 is ideal
        self.pico_acceleration = 150  # [setps/s^2] <<1000 is best for not distrubing CEP lock
        self.pico_min_velocity = 0    # [Hz]
        self.pico_max_velocity = 2000 # [Hz]

        hbmain = QtGui.QHBoxLayout()
        
        #vbplt = QtGui.QVBoxLayout()
        grid_layout = QtGui.QGridLayout()
        
        self.plt = pg.PlotWidget()
        self.plt.setLabel('left', "AOM voltage")
        self.plt.showGrid(x=True, y=True)
        self.plt_AOMvoltage     = self.plt.plot(pen='w')
        self.plt_AOMvoltageMean = self.plt.plot(pen='g')
        self.plt_AOMvoltageRangeTop = self.plt.plot(pen='y')
        self.plt_AOMvoltageRangeBot = self.plt.plot(pen='y')
        data = np.random.normal(size=(self.ADC_Nsamples,))
        self.plt_AOMvoltage.setData(x=data,y=data+500)
                
        self.plt2 = pg.PlotWidget()
        self.plt2.setLabel('left', "AOM voltage history")
        self.plt2.showGrid(x=True, y=True)
        self.plt2.setYLink(self.plt)
        self.plt_aomhistory   = self.plt2.plot(pen='w')
        self.plt_aomhistoryMean = self.plt2.plot(pen='g')
        self.plt_aomhistoryRangeTop = self.plt2.plot(pen='y')
        self.plt_aomhistoryRangeBot = self.plt2.plot(pen='y')
        
        self.plt3 = pg.PlotWidget()
        self.plt3.setXLink(self.plt2)
        self.plt3.showGrid(x=True, y=True)
        self.plt3.setLabel('left', "wedge position history")
        self.plt_wedgehistory = self.plt3.plot(pen='w')
        
        grid_layout.addWidget(self.plt2, 0,0)
        #grid_layout.addWidget(self.plt,  0,1) # hide this plot (showing all ADC samples)
        grid_layout.addWidget(self.plt3, 1,0)
        #grid_layout.setColumnStretch(2,1)
        
        #self.plt.setYRange(0,1000)
        #self.plt2.setXRange(0,self.hist_length)
        #self.plt2.setYRange(0,1000)
        #self.plt3.setXRange(0,self.hist_length)#now done after window opened
        
        
        hbmain.addLayout(grid_layout)
              
        vb = QtGui.QVBoxLayout()
        vbhb = QtGui.QHBoxLayout()
         
        self.btn = QtGui.QPushButton('Start ADC', self)
        self.btn.clicked.connect(self.readADCstartstop)
        vbhb.addWidget(self.btn)

        self.quit = QtGui.QPushButton('Quit', self)
        self.quit.clicked.connect(self.close)
        vbhb.addWidget(self.quit)

        vb.addLayout(vbhb)
        #self.pbar = QtGui.QProgressBar(self)
        #vb.addWidget(self.pbar)

        vbhb = QtGui.QHBoxLayout()
        self.info1 = QtGui.QLabel('<AOM voltage> :', self)
        vbhb.addWidget(self.info1)
        self.aomvoltsinfo = QtGui.QLabel(' 0000 mV ', self)
        vbhb.addWidget(self.aomvoltsinfo)
        #self.AOMinfo = QtGui.QLabel('info here', self)
        #vbhb.addWidget(self.AOMinfo)
        vb.addLayout(vbhb)

        vbhb = QtGui.QHBoxLayout()
        l = QtGui.QLabel('setpoint (mV)', self)
        l.setStyleSheet("color: green")
        self.setpoint = QtGui.QSpinBox()
        self.setpoint.setStyleSheet("color: green")
        self.setpoint.setMinimum(100)
        self.setpoint.setMaximum(900)
        self.setpoint.setSingleStep(10)
        self.setpoint.setValue(500)
        self.setpoint.setMinimumHeight(75)
        self.setpoint.valueChanged.connect(self.setPlotInfo)
        vbhb.addWidget(l)
        vbhb.addWidget(self.setpoint)
        vb.addLayout(vbhb)
        
        vbhb = QtGui.QHBoxLayout()
        l = QtGui.QLabel('lockrange (mV)', self)
        l.setStyleSheet("color: yellow")
        self.lockrange = QtGui.QSpinBox()
        self.lockrange.setStyleSheet("color: yellow")
        self.lockrange.setMinimum(10)
        self.lockrange.setMaximum(200)
        self.lockrange.setSingleStep(10)
        self.lockrange.setValue(100)
        self.lockrange.valueChanged.connect(self.setPlotInfo)
        vbhb.addWidget(l)
        vbhb.addWidget(self.lockrange)
        vb.addLayout(vbhb)

        #spacer = QtGui.QLabel('   ', self)
        #vb.addWidget(spacer)

        #fbhb = QtGui.QHBoxLayout()
        self.fb = QtGui.QCheckBox('enable feedback', self)
        self.fb.setCheckable(True)
        vb.addWidget(self.fb)

        self.AOMinfo = QtGui.QLabel('info here', self)
        vb.addWidget(self.AOMinfo)

        self.fbinfo = QtGui.QLabel(' ', self)
        self.fbinfo.setText("not moving")
        self.fbinfo.setMinimumWidth(100)
        vb.addWidget(self.fbinfo)

        #spacer = QtGui.QLabel('   ', self)
        #fbhb.addWidget(spacer)
        #vb.addLayout(fbhb)
        
        #spacer = QtGui.QLabel('   ', self)
        #vb.addWidget(spacer)
        
        #self.wedgemanualbox = QtGui.QGroupBox("Exclusive Radio Buttons")
        vbhb = QtGui.QHBoxLayout()
        vbhbvb1 = QtGui.QVBoxLayout()
        self.wedgestepsizelabel = QtGui.QLabel('wedge steps:', self)
        vbhbvb1.addWidget(self.wedgestepsizelabel)
        self.wedgestepsizeCB = QtGui.QComboBox(self)
        self.wedgestepsizeCB.addItem("10")
        self.wedgestepsizeCB.addItem("100")
        self.wedgestepsizeCB.addItem("200")
        self.wedgestepsizeCB.addItem("400")
        self.wedgestepsizeCB.addItem("18000")
        self.wedgestepsizeCB.setCurrentIndex(2)
        vbhbvb1.addWidget(self.wedgestepsizeCB)
        #self.wedgestepsize.activated[str].connect(self.wedgestepsizeset)
        self.wedgestepsizeCB.activated.connect(self.wedgestepsizeset)
        
        vbhbvb2 = QtGui.QVBoxLayout()
        self.wedge_in = QtGui.QPushButton('move wedge IN', self)
        self.wedge_in.setMinimumHeight(75)
        vbhbvb2.addWidget(self.wedge_in)
        self.wedge_in.clicked.connect(self.movewedgebutton)

        self.wedge_out = QtGui.QPushButton('move wedge OUT', self)
        self.wedge_out.setMinimumHeight(75)
        vbhbvb2.addWidget(self.wedge_out)
        self.wedge_out.clicked.connect(self.movewedgebutton)

        vbhb.addLayout(vbhbvb1)
        vbhb.addLayout(vbhbvb2)
        #self.wedgemanualbox.setLayout(vbhb)
        vb.addLayout(vbhb)

        self.timer = QtCore.QBasicTimer()
        
        #self.setGeometry(300, 300, 500, 400)
        self.setWindowTitle('CEPfastloop')
        self.setStyleSheet("background-color: grey; font-size: 16pt; font-weight: bold; color: white")
        #self.setStyleSheet("font-size: 14pt")
        
        
        hbmain.addLayout(vb)
        self.setLayout(hbmain)
        self.setPlotInfo()
        
        self.AOMvoltage = self.setpoint.value() + np.random.normal(size=(self.ADC_Nsamples,))
        self.iter = 0
        self.wedgestepsizeset()
        
        self.hist_time      = np.zeros(self.hist_length,)
        self.hist_wedgesteps = np.zeros(self.hist_length,)
        self.hist_aomvolts   = np.zeros(self.hist_length,)

        # start serial port:
        self.ser = serial.Serial("/dev/ttyUSB0", baudrate=19200, timeout=3.0)
        time.sleep(1)
        self.ser.write("INI\r\n")
        for picoinin in range(0,10):
            print("initialising picomotor controller %0.0f %%" % (100. * picoinin/10.0))
            time.sleep(1)
       
        self.ser.write("ECHO OFF\r\n")
        time.sleep(1)
        print("initialising picomotor controller %0.0f %%" % (100))

        print("picomotor controller: setting channel A1 motor 0")
        self.ser.write("CHL A1=0\r\n")
        time.sleep(0.5)
        print("picomotor controller: setting acceleration to %i steps/s^2" % (self.pico_acceleration))
        self.ser.write("ACC A1 0=%i\r\n" % self.pico_acceleration) # 16 20000 steps/s^2 set acceleration
        time.sleep(0.5)
        print("picomotor controller: setting min velocity to %i Hz" % (self.pico_min_velocity))
        self.ser.write("MPV A1 0=%i\r\n" % self.pico_min_velocity) # 0 1999 Hz set minimum profile velocity
        time.sleep(0.5)
        print("picomotor controller: setting max velocity to %i Hz" % (self.pico_max_velocity))
        self.ser.write("VEL A1 0=%i\r\n" % self.pico_max_velocity) # 1 2000 Hz set velocity
        time.sleep(0.5)
        print("picomotor ready")
        
        #self.show() # normal window
        self.showFullScreen()# fuillscreen window

        # start the AOM reader timer loop
        self.readADCstartstop()
        
        self.plt.setYRange(0,1000)
        self.plt2.setXRange(0,self.hist_length)
        self.plt2.setYRange(0,1000)
        self.plt3.setXRange(0,self.hist_length)

        
    def timerEvent(self, ee):
        self.hist_time = np.roll(self.hist_time,-1)
        self.hist_time[-1] = time.time()

        #self.hist_time_str = np.roll(self.hist_time_str,-1)
        #self.hist_time_str[-1] = time.strftime("%a, %d %b %Y %H:%M:%S +0000" , time.gmtime() )

        self.hist_aomvolts     = np.roll(self.hist_aomvolts,-1)
        self.hist_aomvolts[-1] = self.hist_aomvolts[-2]

        self.hist_wedgesteps = np.roll(self.hist_wedgesteps,-1)
        self.hist_wedgesteps[-1] = self.hist_wedgesteps[-2]
       
        self.iter = self.iter + 1.
        
        self.readADC()
        self.feedback()
        self.setAOMinfo()
        self.plotting()
        self.logging()


    def readADC(self):
        if self.testing == 1:
            self.AOMvoltage = np.mean(self.AOMvoltage) + 10 * np.random.normal(size=(self.ADC_Nsamples,)) + 5*np.sin(self.iter*0.05)
        elif self.testing == 0:
            # read AOM voltage via Adafruit ADS1015
            for n in range(0,self.ADC_Nsamples):
                #volts = adc.readADCSingleEnded(0, 1024, 3300) / 1000
                volts = self.adc.readADCDifferential(0,1, 6144, 3300) / 1000
                #volts=adc.getLastConversionResults()/1000
                self.AOMvoltage[n] = volts * 1000. +830.
                
        self.AOMvoltageMean    = np.mean(self.AOMvoltage)
        #self.hist_aomvolts     = np.roll(self.hist_aomvolts,-1)
        self.hist_aomvolts[-1] = self.AOMvoltageMean
        
        
    def readADCstartstop(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn.setText('Start ADC')
        else:
            self.adc = ads1x15(ic=0x00)
            self.timer.start(100, self)
            self.btn.setText('Stop ADC')
        
                
    def logging(self):
        if self.iter >= self.hist_length:
            self.iter = 0
            print("logging data to file")
            with open('/home/pi/CEPfastloop.log','a') as f_handle:
                np.savetxt(f_handle, (np.transpose([self.hist_time, self.hist_aomvolts, self.hist_wedgesteps])), delimiter=', ', fmt='%.23f, %.1f, %i')


    def plotting(self):
        self.plt_AOMvoltage.setData(self.AOMvoltage)
        self.plt_aomhistory.setData(   self.hist_aomvolts)
        self.plt_wedgehistory.setData( self.hist_wedgesteps)
        #self.plt_aomhistory.setData(   x=self.hist_time-self.hist_time[0], y=self.hist_aomvolts)
        #self.plt_wedgehistory.setData( x=self.hist_time-self.hist_time[0], y=self.hist_wedgesteps)
        #print "iter: %i" % (self.iter)

    def feedback(self):
        if self.fb.isChecked():
            if self.AOMvoltageMean >= self.setpoint.value() + self.lockrange.value():
                self.feedbackactive = -15
            if self.AOMvoltageMean <= self.setpoint.value() - self.lockrange.value():
                self.feedbackactive = 15
        elif not self.fb.isChecked():
            self.stopfeedback()
            #self.hist_wedgesteps = np.roll(self.hist_wedgesteps,-1)
            #self.hist_wedgesteps[-1] = self.hist_wedgesteps[-2]

        # we want the wedge to be moved until the AOM voltage reached the setpoint again
        # otherwise the voltage will hover at the max or min of the lockrange and feedback is constantly on and distrubing the oscillator
        if self.feedbackactive > 0 :
            self.feedbackactive = self.feedbackactive - 1
            self.wedgemover(self.feedbackstepsize)
            self.fbinfo.setText("moving wedge in")
            self.fbinfo.setStyleSheet("color: orange")
            if self.AOMvoltageMean > self.setpoint.value() :
                self.stopfeedback()
        if self.feedbackactive < 0 :
            self.feedbackactive = self.feedbackactive + 1
            self.wedgemover(-self.feedbackstepsize)
            self.fbinfo.setText("moving wedge out")
            self.fbinfo.setStyleSheet("color: orange")
            if self.AOMvoltageMean < self.setpoint.value() :
                self.stopfeedback()
        if self.feedbackactive == 0:
            self.stopfeedback()
            #self.hist_wedgesteps[-1] = self.hist_wedgesteps[-2]
    
    def stopfeedback(self):
        self.feedbackactive = 0
        self.fbinfo.setText("not moving")
        self.fbinfo.setStyleSheet("color: green")
        
    def setAOMinfo(self):
        #print "AOMvoltageMean = %.1f" % (self.AOMvoltageMean)
        self.aomvoltsinfo.setText(" %.0f mV " % (self.AOMvoltageMean))
        
        self.AOMinfo.setStyleSheet("color: green")
        self.AOMinfo.setText("AOM voltage ok")
        
        if self.AOMvoltageMean >= self.setpoint.value() + self.lockrange.value() or self.AOMvoltageMean <= self.setpoint.value() - self.lockrange.value() :
            self.AOMinfo.setStyleSheet("color: orange")
            self.AOMinfo.setText("AOM voltage warning")
            
        if self.AOMvoltageMean >= 900 or self.AOMvoltageMean <= 100:
            self.AOMinfo.setStyleSheet("color: red")
            self.AOMinfo.setText("AOM voltage critical")
        
    def setPlotInfo(self):
        #y = np.random.normal(size=(self.ADC_Nsamples,)) * 0
        y = np.zeros(self.ADC_Nsamples,)
        self.plt_AOMvoltageMean.setData(     y + self.setpoint.value() )
        self.plt_AOMvoltageRangeTop.setData( y + self.setpoint.value() + self.lockrange.value())
        self.plt_AOMvoltageRangeBot.setData( y + self.setpoint.value() - self.lockrange.value())
        y = np.zeros(self.hist_length,)
        self.plt_aomhistoryMean.setData(     y + self.setpoint.value() )
        self.plt_aomhistoryRangeTop.setData( y + self.setpoint.value() + self.lockrange.value())
        self.plt_aomhistoryRangeBot.setData( y + self.setpoint.value() - self.lockrange.value())
        

    def wedgestepsizeset(self): #, text):
        #self.wedgestepsize = int(text)
        self.wedgestepsize = int( self.wedgestepsizeCB.currentText() )
        print("stepsize set to: %i" % (self.wedgestepsize))


    def movewedgebutton(self):
        #print "moving wedge in by %i steps" % (self.wedgestepsize)
        #source = self.sender()
        sender = self.sender()
        #print "%s" % (sender.text())
        #self.hist_wedgesteps = np.roll(self.hist_wedgesteps,-1)
        
        if sender.text() == "move wedge IN":
            self.wedgemover(self.wedgestepsize)
            #self.hist_wedgesteps[-1] = self.hist_wedgesteps[-2] + self.wedgestepsize
            
        if sender.text() == "move wedge OUT":
            self.wedgemover(-self.wedgestepsize)
            #self.hist_wedgesteps[-1] = self.hist_wedgesteps[-2] - self.wedgestepsize
    
    def wedgemover(self, steps):
        #print "moving wedge by %i steps" % (steps)
        #self.hist_wedgesteps = np.roll(self.hist_wedgesteps,-1)
        self.hist_wedgesteps[-1] = self.hist_wedgesteps[-2] + steps #log step history
        # TODO add code to talk to picomotor via serial port here
        #self.AOMvoltage = self.AOMvoltage + steps  # this is jsut to fake a wedge move

        #self.ser.write("ACC A1 0=160\r\n") # 16 20000 steps/s^2 set acceleration
        #time.sleep(0.1)
        #self.ser.write("MPV A1 0=0\r\n") # 0 1999 Hz set minimum profile velocity
        #time.sleep(0.1)
        #self.ser.write("VEL A1 0=2000\r\n") # 1 2000 Hz set velocity
        #time.sleep(0.1)


        self.ser.write("REL A1 %i\r\n" % steps)
        time.sleep(0.1)
        self.ser.write("GO\r\n")
        time.sleep(0.1)

        #this is the old code for remote feedback via FIACS on pointium
        #fn = '/home/pi/mnt_pointium/newfocuspicomotor_request_' + str(steps)
        #print "fn = %s" % (fn)
        #with open(fn,'a') as f_handle:
        #    np.savetxt(f_handle, ([0]))

def main():
    app = QtGui.QApplication(sys.argv)
    ex = CEPfastloop()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()   
