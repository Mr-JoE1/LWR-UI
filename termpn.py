#!/usr/bin/env python3.8

################################################################################
#   \file
#   \author     <a href="https://www.infinitytech.ltd">innomatic</a>
#   \brief      wxPython Laser Warning System.
#   \Date        20/10/2020
################################################################################

import os
#import winsound
import time
import wx
import wx.adv
import pickle
import serial
import wx.lib.newevent
import _thread
import numpy as np
import RPi.GPIO as GPIO
from SerialCom import *
from _codecs import utf_8_decode
from sys import getsizeof
#from win32ui import GetType
from builtins import len, ord
from matplotlib import streamplot
from binascii import hexlify

# RPI pins def
# start button--17
# stop button--27
# mode button--22
# left relay--18
# right relay--23
# buzzer--24


#GPIO.cleanup()
# new event class for the COM thread
(UpdateComData, EVT_UPDATE_COMDATA) = wx.lib.newevent.NewEvent()
(UpdateAngle, EVT_UPDATE_ANGLE) = wx.lib.newevent.NewEvent()
(UpdateMsg, EVT_UPDATE_COMMSG) = wx.lib.newevent.NewEvent()
(ManStop, RPI_STOP_BUTTON) = wx.lib.newevent.NewEvent()
(ManStart, RPI_START_BUTTON) = wx.lib.newevent.NewEvent()
(ManMode, RPI_MODE_BUTTON) = wx.lib.newevent.NewEvent()
# default data file name
data_file = 'LWR_log.txt'
# RPI PIN schem mode
GPIO.setmode(GPIO.BCM)
# RPI PIN DIRECTION
GPIO.setwarnings(False)
GPIO.setup(24,GPIO.OUT)
GPIO.setup(23,GPIO.OUT)
GPIO.setup(18,GPIO.OUT)
GPIO.setup(17,GPIO.IN, pull_up_down= GPIO.PUD_DOWN)
GPIO.setup(27,GPIO.IN, pull_up_down= GPIO.PUD_DOWN)
GPIO.setup(22,GPIO.IN, pull_up_down= GPIO.PUD_DOWN)

global fname

def GpioControl(self,fn):
    # RPI PIN schem mode
    GPIO.setmode(GPIO.BCM)
    # RPI PIN DIRECTION
    GPIO.setwarnings(False)
    GPIO.setup(24,GPIO.OUT)
    GPIO.setup(23,GPIO.OUT)
    GPIO.setup(18,GPIO.OUT)
    GPIO.setup(17,GPIO.IN, pull_up_down= GPIO.PUD_DOWN)
    GPIO.setup(27,GPIO.IN, pull_up_down= GPIO.PUD_DOWN)
    GPIO.setup(22,GPIO.IN, pull_up_down= GPIO.PUD_DOWN)
    # fire alarm
    if fn==1:
        #print("alarm")
        GPIO.output(24, GPIO.HIGH)
        time.sleep(0.04)
        GPIO.output(24, GPIO.LOW)
    # Manual mode select
    if fn==2:
        if GPIO.input(22):
            #print("SMOKE")
            GPIO.output(23, GPIO.HIGH)
            GPIO.output(18, GPIO.HIGH)
        else:
            GPIO.output(23, GPIO.LOW)
            GPIO.output(18, GPIO.LOW)
            #GPIO.cleanup()
    #Manual Stop
    elif fn==3:
        if GPIO.input(27):
            evt = ManStop()
            wx.PostEvent(self.win , evt)
            #print("stop")
        else:
            pass
            #print("no stop")
    elif fn==5:
        #GPIO.wait_for_edge(17, GPIO.RISING)
        evt = ManStart()
        wx.PostEvent(self,evt)

    #Manual Mode select
    elif fn==6:
        if GPIO.input(22):
            evt = ManMode(data=True)
            wx.PostEvent(self.win , evt)
            #print("stop")
        else:
            evt = ManMode(data=False)
            wx.PostEvent(self.win , evt)




def GetMonoFont():

    if os.name == 'nt':
        fname = 'Consolas'
        return fname

    # unknown OS
    else:
        fname = 'helvetica'#wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        return fname

 # ===========================================================================
 # OM port listening thread.
 # Make sure that this thead starts after the port is open and
 # stops before the port is closed. Also the timeout value of
 # the port should be set preferably with small value
 # ===========================================================================


class ComThread:

    def __init__(self, win, ser):
        # window to which the receiving data is sent
        self.win = win
        # serial port
        self.ser =ser
        # initial state
        self.running = False
    # call this method to start the thread.

    def Start(self):
        self.keepGoing = True
        self.running = True
        _thread.start_new_thread(self.Run, ())

    # signal the thread to suicide
    def Stop(self):
        # flag for nice termination
        self.keepGoing = False

    # main routine: upon arrival of new data, it generates an event.
    def Run(self):
        # global  self.ang

        # keep running as far as the flag is set
        while self.keepGoing:
            # read a byte until timeout
            data = self.ser.read(1)
            # STOP THREAD USING BUTTON GPIO.27
#             data = bytearray(data.strip(), 'utf-8')

            # valid byte received
            if data == b'\xa4':
                GpioControl(self,1)
                ms= self.ser.read(11)
                msg = UpdateMsg(data=ms)
                # post the event for decode fun
                wx.PostEvent(self.win, msg)
                evt = UpdateComData(data=ms)
                # post the event for terminal
                wx.PostEvent(self.win, evt)

                #play alert sound using GPIO.24

                #winsound.Beep(750, 50)

            else:
                GpioControl(self,3) #Manual Stop

                GpioControl(self,6)
                # create an event with the byte
                evt = UpdateComData(data=data)
                # post the event
                wx.PostEvent(self.win, evt)

        # end of loop
        self.running = False

    # return True if the thread is running
    def IsRunning(self):
        return self.running

    # change the target window for the event
    def SetEventTarget(self, win):
        self.win = win

 # ===========================================================================
 # Creat bottom panel for control buttons and serial terminal
 # ===========================================================================


class ConPanel(wx.Panel):
    def __init__(self, parent, ser, **kwgs):
        wx.Panel.__init__(self, parent, **kwgs)
        self.parent = parent
        self.SetBackgroundColour('black')
        fname = GetMonoFont()
        # serial port
        self.ser = ser

        # packet decoder
        self.pd = PacketDecoder()
        self.pd.SetMode('decode')

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.data1 = wx.TextCtrl(
                self, wx.ID_ANY, "--", size=(80, 55), style=wx.TE_CENTRE)
        self.data1.SetFont(wx.Font(20, 75, 90, 90, faceName=fname))
        self.data1.SetForegroundColour('red')
        self.data1.SetBackgroundColour('white')
        self.data1.SetMaxLength(5)
        hbox1.Add(self.data1, flag=wx.LEFT, border=8)

        txt1 = wx.StaticText(self, label="الزاوية")
        txt1.SetForegroundColour('yellow')
        txt1.SetFont(wx.Font(20,75, 90, 90, faceName=fname))
        hbox1.Add(txt1, flag=wx.LEFT, border=8)

        vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)

        vbox.Add((-1, 10))

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.data2 = wx.TextCtrl(
                self, wx.ID_ANY, "--", size=(80, 55), style=wx.TE_CENTRE)
        self.data2.SetFont(wx.Font(20, 75, 90, 90, faceName=fname))
        self.data2.SetForegroundColour('red')
        self.data2.SetBackgroundColour('white')
        self.data2.SetMaxLength(5)
        hbox2.Add(self.data2, flag=wx.LEFT, border=8)

        txt2 = wx.StaticText(self, label="التردد")
        txt2.SetForegroundColour('yellow')
        txt2.SetFont(wx.Font(20,75, 90, 90, faceName=fname))
        hbox2.Add(txt2, flag=wx.LEFT, border=8)

        vbox.Add(hbox2, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)

        vbox.Add((-1, 10))

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)

        self.data3 = wx.TextCtrl(self, wx.ID_ANY, "--",
                            size=(80, 50), style=wx.TE_CENTRE)
        self.data3.SetFont(wx.Font(20, 75, 90, 90, faceName=fname))
        self.data3.SetForegroundColour('red')
        self.data3.SetBackgroundColour('white')
        self.data3.SetMaxLength(4)

        hbox3.Add(self.data3, flag=wx.LEFT, border=8)

        txt3 = wx.StaticText(self, label='النوع')
        txt3.SetForegroundColour('yellow')
        txt3.SetFont(wx.Font(20, 75, 90, 90, faceName=fname))
        hbox3.Add(txt3, flag=wx.LEFT, border=8)

        vbox.Add(hbox3, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)
        
        
        hbox555 = wx.BoxSizer(wx.HORIZONTAL)
        vbox.Add((-1, 10))

        self.data5 = wx.TextCtrl(self, wx.ID_ANY, "أرضي",
                            size=(80, 50), style=wx.TE_CENTRE)
        self.data5.SetFont(wx.Font(20, 75, 90, 90, faceName=fname))
        self.data5.SetForegroundColour('red')
        self.data5.SetBackgroundColour('white')
        self.data5.SetMaxLength(4)

        hbox555.Add(self.data5, flag=wx.LEFT, border=8)

        txt5 = wx.StaticText(self, label='التهديد')
        txt5.SetForegroundColour('yellow')
        txt5.SetFont(wx.Font(20, 75, 90, 90, faceName=fname))
        hbox555.Add(txt5, flag=wx.LEFT, border=8)

        vbox.Add(hbox555, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)

        vbox.Add((-1, 10))
        

        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        self.data4 = wx.TextCtrl(self, wx.ID_ANY, "يدوي",
                            size=(80,50 ), style= wx.TE_CENTRE )
        self.data4.SetFont(wx.Font(20, 75, 90, 90, faceName=fname))
        self.data4.SetForegroundColour('red')
        self.data4.SetBackgroundColour('white')
        self.data4.SetMaxLength(4)
        hbox4.Add(self.data4, flag=wx.LEFT, border=8)


        txt4 = wx.StaticText(self, label='تشغيل')
        txt4.SetForegroundColour('yellow')
        txt4.SetFont(wx.Font(20, 75, 90, 90, faceName=fname))
        hbox4.Add(txt4, flag=wx.LEFT, border=8)


        vbox.Add(hbox4, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)

        vbox.Add((-1, 10))

        ######################################
        # Touch Control Buttons
        ######################################
        hbox5 = wx.BoxSizer(wx.HORIZONTAL)
        btn1 = wx.Button(self, label='بدأ', size=(70,40))
        btn1.SetForegroundColour('black')
        btn1.SetBackgroundColour('green')
        btn1.SetFont(wx.Font(16, 75, 90, 90, faceName=fname))
        hbox5.Add(btn1, flag=wx.LEFT, border=8)

        btn2 = wx.ToggleButton(self, label='الوضع', size=(70,40))
        btn2.SetForegroundColour('black')
        btn2.SetBackgroundColour('white')
        btn2.SetFont(wx.Font(12, 75, 90, 90, faceName=fname))
        hbox5.Add(btn2,flag=wx.LEFT, border=8)
        vbox.Add(hbox5, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)

        vbox.Add((-1, 5))
        hbox6 = wx.BoxSizer(wx.HORIZONTAL)
        self.btn4 = wx.Button(self, label='إيقاف', size=((70,40)))
        self.btn4.SetForegroundColour('black')
        self.btn4.SetBackgroundColour('red')
        self.btn4.SetFont(wx.Font(14, 75, 90, 90, faceName=fname))
        hbox6.Add(self.btn4, flag=wx.LEFT, border=8)
        btn3 = wx.Button(self, label='Info', size=(70,40))
        btn3.SetForegroundColour('black')
        btn3.SetBackgroundColour('white')
        btn3.SetFont(wx.Font(14, 75, 90, 90, faceName=fname))
        hbox6.Add(btn3, flag=wx.LEFT, border=8)
        vbox.Add(hbox6, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=5)

        vbox.Add((-1, 5))
        self.SetSizer(vbox)


        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        # CREATED EVENTS HANDLING
        self.Bind(EVT_UPDATE_COMMSG, self.OnUpdateComMsg)
        self.Bind(RPI_STOP_BUTTON, self.OnStop)
        self.Bind(RPI_START_BUTTON, self.OnPortOpen)
        self.Bind(RPI_MODE_BUTTON, self.OnMood)

        # Control  buttons Events objects

        btn1.Bind(wx.EVT_BUTTON, self.OnPortOpen)
        btn2.Bind(wx.EVT_TOGGLEBUTTON, self.OnMood)
        self.btn4.Bind(wx.EVT_BUTTON, self.OnStop)
        btn3.Bind(wx.EVT_BUTTON, self.OnAbout)

        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

 # ===========================================================================
 # Handling Config Choices events
 # ===========================================================================
 # COM thread object
        self.thread = ComThread(self, self.ser)

        # raw data storage
        self.rawdata = bytearray()
        self.rawdata2 = bytearray()
        self.ang = ""
        # event list
        self.lstEvent = None

    def IntCallback(self,channel):
        evt = ManStart()
        wx.PostEvent(self,evt)
        #GPIO.cleanup()

    # Put your checksum algorithm here
    def ComputeChecksum(self, data):
        return 0x00

    # Put your packet decoding algorithm here
    def DecodePacket(self, data):
        pass

    # Reset raw data. Terminal will be cleared as well.
    def ResetData(self):
        #self.rawdata.append(ord('RST'))
        self.ClearTerminal()
        self.ang=0
        wx.PostEvent(self.parent, UpdateAngle(data=self.ang))
        self.data1.Clear()
        self.data2.Clear()
        self.data3.Clear()
        self.data4.Clear()


    # Open COM port
    def OpenPort(self, port, speed):

        if self.ser.is_open:
            # terminate thread first
            if self.thread.IsRunning():
                self.thread.Stop()
            # join the thread
            while self.thread.IsRunning():
                wx.MilliSleep(100)
            # then close the port
            self.ser.close()

        # set port number and speed
        self.ser.port = port
        self.ser.baudrate = int(speed)
        # setting read timeout is crucial for the safe termination of thread
        self.ser.timeout = 1

        # open the serial port
        try:
            self.ser.open()
        except:
            return False
        else:
            pass

        if self.ser.is_open:
            # start thread
            self.thread.Start()
            return True
        else:
            return False

    # Save received data
    def SaveRawData(self, data_file):
        dout= self.rawdata.hex()
        f = open(data_file, 'wb')
        pickle.dump(dout, f)
        f.close()

    def OnMood(self, evt):
        #state= evt.GetEventObject().GetValue()
        if evt.data == True:
            self.mood="آلي"
            #Auto firing Mode

        else:
            self.mood="يدوي"


        self.data4.Clear()
        self.data4.AppendText(self.mood)
    def OnStop(self, evt):
        # terminate the thread
        if self.thread.IsRunning():
            self.thread.Stop()
        # join the thread
        while self.thread.IsRunning():
            wx.MilliSleep(100)

        # close the port
        if self.ser.is_open:
            self.ser.close()

        self.data1.Clear()
        self.data1.AppendText("--")
        self.data2.Clear()
        self.data2.AppendText("--")
        self.data3.Clear()
        self.data3.AppendText("--")
        #GPIO.cleanup()
        wx.PostEvent(self.parent, UpdateAngle(data=0))
        #GpioControl(self,5)

# Port selection choice handler
    def OnPortOpen(self, evt):
        port = '/dev/ttyS0'
        speed = '115200'

        # device is not selected
        if port == '':
            return

        # open the com port
        if self.OpenPort(port, speed):
             pass
        else:
            wx.MessageBox('Failed to open: ' + port)


    # COM data input handler
    def OnUpdateComMsg(self, msg):
        self.rawdata2 = msg.data if isinstance(
            msg.data, bytearray) else bytearray(msg.data)
        dd= ':'.join('{:02x}'.format(x) for x in self.rawdata2)
        #print(dd)
        #print(self.rawdata2)

        #decode thread angel and creat event
        if dd[6] == '6' and dd[7]=='4':

            if dd[7] == '4' and dd[9] == '0' and dd[10] == '1':
                    self.ang = '22'
            elif dd[7] == '4' and dd[9] == '0' and dd[10] == '2':
                    self.ang = '45'
            elif dd[7] == '4' and dd[9] == '0' and dd[10] == '3':
                    self.ang = '67'
            elif dd[7] == '4' and dd[9] == '0' and dd[10] == '4':
                    self.ang = '90'
            elif dd[7] == '4' and dd[9] == '0' and dd[10] == '5':
                    self.ang = '112'
            elif dd[7] == '4' and dd[9] == '0' and dd[10] == '6':
                    self.ang = '135'
            elif dd[7] == '4' and dd[9] == '0' and dd[10] == '7':
                    self.ang = '157'
            elif dd[7] == '4' and dd[9] == '0' and dd[10] == '8':
                    self.ang = '180'
            elif dd[7] == '4' and dd[9] == '0' and dd[10] == '9':
                    self.ang = '202'
            elif dd[7] == '4' and dd[9] == '1' and dd[10] == '0':
                    self.ang = '225'
            elif dd[7] == '4' and dd[9] == '1' and dd[10] == '1':
                    self.ang = '247'
            elif dd[7] == '4' and dd[9] == '1' and dd[10] == '2':
                    self.ang = '270'
            elif dd[7] == '4' and dd[9] == '1' and dd[10] == '3':
                    self.ang = '292'
            elif dd[7] == '4' and dd[9] == '1' and dd[10] == '4':
                    self.ang = '315'
            elif dd[7] == '4' and dd[9] == '1' and dd[10] == '5':
                self.ang = '337'
            elif dd[7] == '4' and dd[9] == '1' and dd[10] == '6':
                self.ang = '360'
            else:
                self.ang = "0"
            wx.PostEvent(self.parent, UpdateAngle(data=self.ang))
            self.data1.Clear()
            self.data1.AppendText(self.ang)
            if int(self.ang) > 0 :
                GpioControl(self,2) # Auto fire check
            if dd[12] == '0' and dd[13] == '1':
                self.data5.Clear()
                self.data1.AppendText("جوي")
            else:
                self.data5.Clear()
                self.data5.AppendText("أرضي")
            #decode freq and laser thread type
            s= dd[24]+dd[25]+dd[21]+dd[22]+dd[18]+dd[19]+dd[15]+dd[16]
            counts = int(s, 16)
            counts_time= counts*(20/(10**9))
            # dispaly count time
            hz= round((1/counts_time),2)
            tms= counts*(20/(10**6))

            if hz >= 1  and hz <=7 :
                self.type = 'LRF'
            elif hz > 7  and hz <=25 :
                self.type = 'LTD'
            elif hz >= 1000  :
                self.type = 'BR'
            else:
                self.type = 'None'

            self.freq= str(hz)
            #self.tt= str(tms)
            #self.data2.Clear()
            #self.data2.AppendText(self.tt)
            self.data2.Clear()
            self.data2.AppendText(self.freq)
            self.data3.Clear()
            self.data3.AppendText(self.type)


            self.rawdata2 = bytearray()
            dd = ''



 # ===========================================================================
 # Handling bottom panel  Buttons
 # ===========================================================================
    # wx.EVT_CLOSE handler
    def OnClose(self, e):
        # terminate the thread
        if self.thread.IsRunning():
            self.thread.Stop()
        # join the thread
        while self.thread.IsRunning():
            wx.MilliSleep(100)

        # close the port
        if self.ser.is_open:
            self.ser.close()

        # destroy self
        self.Destroy()
    # Events Handling FUNCTIONS

    def OnCloseWindow(self, e):

        dial = wx.MessageDialog(None, 'Are you sure to quit?', 'Question',
                                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)

        ret = dial.ShowModal()

        if ret == wx.ID_YES:
            self.OnClose(e)

        else:
            e.Skip()

    # handels pressing ESC keyboard key
    def OnKeyDown(self, e):

        key = e.GetKeyCode()

        if key == wx.WXK_ESCAPE:

            ret = wx.MessageBox('Are you sure to quit?', 'Question',
                                wx.YES_NO | wx.NO_DEFAULT, self)

            if ret == wx.YES:
                self.OnClose(e)
                self.Close()
            else:
                e.Skip()

    # handels About Button
    def OnAbout(self, event):

        description = """ LWR Tracker, Is a custom tool related to
         Laser warning system
         Made by TRC of Egyption Armed Forces which
         moniter Laser threats over RS458 Communication.
        """

        licence = """LWR Tracker, is custom tool developed by
        InfinityTech Ltd and licensed under Simple Machines License (SMF1.1).
        See the simple machine License for more details. You should have
        received a copy of the GNU Simple Machine License along with LWR Tracker;
        if not, write to the GNU Software Foundation, Inc., 59 Temple Place,
        Suite 330, Boston, MA  02111-1307  USA
         """

        info = wx.adv.AboutDialogInfo()
        # info.SetBackgroundColour('DIM GREY')
        info.SetIcon(wx.Icon('/home/pi/LWR_RPI_v0.1/logo.png', wx.BITMAP_TYPE_PNG))
        info.SetName('LWR Tracker')
        info.SetVersion('1.0')
        info.SetDescription(description)
        info.SetLicence(licence)
        info.SetCopyright('(C) 2011 - 2020 ')
        info.AddDeveloper('Infinity Tech Ltd')
        info.AddDocWriter('Technical Research Center of Egyption Armed Forces')
        info.SetWebSite('https://infinitytech.ltd')
        wx.adv.AboutBox(info)
channel=17
#GPIO.add_event_detect(17,GPIO.RISING, callback=ConPanel.IntCallback, bouncetime=300)

 # ===========================================================================
 # Adding Panels to the main frame using Splitter
 # ===========================================================================


class LwrFrame(wx.Frame):

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent=None, title="LWR Tracker ")
     # serial terminal panel
        self.pnlTerm = ConPanel(self, serial.Serial(
            '/dev/pts/16'), size=(100, 480))
        # sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.pnlTerm, 1, wx.EXPAND)

        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.sizer.Fit(self)
        self.Show()

        # splitter = wx.SplitterWindow(self)
        # top = RadarGraph(splitter)
        # bottom = ConPanel(splitter, top)
        # splitter.SplitHorizontally(top, bottom)
        # splitter.SetMinimumPaneSize(340)


def main():

    app = wx.App(False)
    ex = LwrFrame(None, "LWR Serial Panel")
    app.MainLoop()


if __name__ == '__main__':
    main()
