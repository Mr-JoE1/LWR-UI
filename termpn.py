#!/usr/bin/env python3.8

################################################################################
#   \file
#   \author     <a href="https://www.infinitytech.ltd">innomatic</a>
#   \brief      wxPython Laser Warning System.
#   \Date        20/10/2020
################################################################################

import os
import winsound 
import time
import wx
import wx.adv
import pickle
import serial
import wx.lib.newevent
import _thread
import numpy as np
from SerialCom import *
from _codecs import utf_8_decode
from sys import getsizeof
from win32ui import GetType
from builtins import len, ord
from matplotlib import streamplot


# new event class for the COM thread
(UpdateComData, EVT_UPDATE_COMDATA) = wx.lib.newevent.NewEvent()
(UpdateAngle, EVT_UPDATE_ANGLE) = wx.lib.newevent.NewEvent()
(UpdateMsg, EVT_UPDATE_COMMSG) = wx.lib.newevent.NewEvent()

# default data file name
data_file = 'LWR_log.txt'

global fname


def GetMonoFont():

    # do not consider the case of osx
    if os.name == 'posix':
        # fc-match will give default monospace font name
        a = os.popen('fc-match "Monospace"').read()
        # face name is burried in the middle
        l = a.find('"')
        r = a.find('"', l+1)
        return a[l+1:r]

    # Windows has only a couple of monospace fonts
    elif os.name == 'nt':
        fname = 'Consolas'
        return fname

    # unknown OS
    else:
        fname = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
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
        self.ser = ser
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

#             data = bytearray(data.strip(), 'utf-8')

            # valid byte received
            if data == b'\xa4':
                ms= self.ser.read(11)
                msg = UpdateMsg(data=ms)
                # post the event for decode fun
                wx.PostEvent(self.win, msg)
                evt = UpdateComData(data=ms)
                # post the event for terminal 
                wx.PostEvent(self.win, evt)
    
                #play alert sound for threads using Beepy Lib    
                winsound.Beep(750, 50)
                
            else:
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

        # Terminal Layout
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.txtTerm = wx.TextCtrl(
            self, -1, "", size=(460, 120), style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.txtTerm.SetForegroundColour('yellow')
        self.txtTerm.SetBackgroundColour('black')
        self.txtTerm.SetFont(wx.Font(11, 75, 90, 90, faceName=fname))
        hbox2.Add(self.txtTerm, proportion=1, border=8)
        vbox.Add(hbox2, proportion=1, flag=wx.LEFT |
                 wx.RIGHT | wx.BOTTOM | wx.EXPAND, border=10)
        vbox.Add((-1, 5))

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)

        txt1 = wx.StaticText(self, label='Angle')
        txt1.SetForegroundColour('yellow')
        txt1.SetFont(wx.Font(12, 75, 90, 90, faceName=fname))
        hbox3.Add(txt1, flag=wx.LEFT, border=8)

        self.data1 = wx.TextCtrl(
            self, wx.ID_ANY, "", size=(50, 25), style=wx.TE_CENTRE)
        self.data1.SetFont(wx.Font(13, 75, 90, 90, faceName=fname))
        self.data1.SetForegroundColour('red')
        self.data1.SetBackgroundColour('black')
        self.data1.SetMaxLength(4)
        hbox3.Add(self.data1, flag=wx.LEFT, border=2)

        txt2 = wx.StaticText(self, label="T(ms)")
        txt2.SetForegroundColour('yellow')
        txt2.SetFont(wx.Font(13, 75, 90, 90, faceName=fname))
        hbox3.Add(txt2, flag=wx.LEFT, border=8)
        
        
 ################# HERE IS THE ANGLE TEXT OUTPUT #######################

        self.data2 = wx.TextCtrl(
            self, wx.ID_ANY, "", size=(50, 25), style=wx.TE_CENTRE)
        self.data2.SetFont(wx.Font(13, 75, 90, 90, faceName=fname))
        self.data2.SetForegroundColour('red')
        self.data2.SetBackgroundColour('black')
        self.data2.SetMaxLength(4)
        hbox3.Add(self.data2, flag=wx.LEFT, border=2)

        txt3 = wx.StaticText(self, label='F(HZ)')
        txt3.SetForegroundColour('yellow')
        txt3.SetFont(wx.Font(13, 75, 90, 90, faceName=fname))
        hbox3.Add(txt3, flag=wx.LEFT, border=8)

        self.data3 = wx.TextCtrl(self, wx.ID_ANY, "",
                            size=(50, 25), style=wx.TE_CENTRE)
        self.data3.SetFont(wx.Font(13, 75, 90, 90, faceName=fname))
        self.data3.SetForegroundColour('red')
        self.data3.SetBackgroundColour('black')
        self.data3.SetMaxLength(4)
        hbox3.Add(self.data3, flag=wx.LEFT, border=2)

        txt4 = wx.StaticText(self, label='Type')
        txt4.SetForegroundColour('yellow')
        txt4.SetFont(wx.Font(11, 75, 90, 90, faceName=fname))
        hbox3.Add(txt4, flag=wx.LEFT, border=8)

        self.data4 = wx.TextCtrl(self, wx.ID_ANY, "",
                            size=(50, 25), style= wx.TE_CENTRE )
        self.data4.SetFont(wx.Font(13, 75, 90, 90, faceName=fname))
        self.data4.SetForegroundColour('red')
        self.data4.SetBackgroundColour('black')
        self.data4.SetMaxLength(4)
        hbox3.Add(self.data4, flag=wx.LEFT, border=2)

        vbox.Add(hbox3, proportion=1, flag=wx.EXPAND |
                 wx.LEFT | wx.RIGHT | wx.ALL, border=5)
        vbox.Add((-1, 5))

        # Config Buttons Layout

        # list of available COM ports
        from serial.tools import list_ports
        portlist = [port for port, desc, hwin in list_ports.comports()]

        hbox5 = wx.BoxSizer(wx.HORIZONTAL)

        # baudrate selection
        self.cboSpeed = wx.Choice(self, -1,
                                  choices=['9600', '19200', '38400', '57800', '115200', '230400'], size=(70, 20), style=wx.TE_CENTRE)
        self.cboSpeed.SetStringSelection('115200')
        hbox5.Add(self.cboSpeed, flag=wx.LEFT, border=2)

        # port selection
        self.cboCPort = wx.Choice(
            self, -1, choices=portlist, size=(70, 20), style=wx.TE_CENTRE)
        hbox5.Add(self.cboCPort, flag=wx.LEFT, border=2)

        # terminal mode selection
        self.cboTMode = wx.Choice(self, -1,
                                  choices=['ASCII', 'Hex', 'Protocol'], size=(70, 20), style=wx.TE_CENTRE)
        self.cboTMode.SetStringSelection('Hex')
        hbox5.Add(self.cboTMode, flag=wx.LEFT, border=2)

        # newline character
        self.cboNLine = wx.Choice(self, -1,
                                  choices=['LF(0x0A)', 'CR(0x0D)'], size=(70, 20), style=wx.TE_CENTRE)
        self.cboNLine.SetStringSelection('LF(0x0A)')
        hbox5.Add(self.cboNLine, flag=wx.LEFT, border=2)

        # local echo
        self.choLEcho = wx.Choice(self, -1,
                                  choices=['Yes', 'No'], size=(70, 20), style=wx.TE_CENTRE)
        self.choLEcho.SetStringSelection('No')
        hbox5.Add(self.choLEcho, flag=wx.LEFT, border=2)

        vbox.Add(hbox5, proportion=1, flag=wx.CENTRE, border=5)
        vbox.Add((-1, 5))

        # Control Buttons Layout

        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        btn1 = wx.Button(self, label='Save', size=(70, 30))
        btn1.SetForegroundColour('yellow')
        btn1.SetBackgroundColour('black')
        hbox4.Add(btn1, border=10)

        btn2 = wx.Button(self, label='Clear', size=(70, 30))
        btn2.SetForegroundColour('yellow')
        btn2.SetBackgroundColour('black')
        hbox4.Add(btn2, border=10)

        btn4 = wx.Button(self, label='Reset', size=(70, 30))
        btn4.SetForegroundColour('yellow')
        btn4.SetBackgroundColour('black')
        hbox4.Add(btn4, flag=wx.LEFT | wx.BOTTOM)

        btn3 = wx.Button(self, label='About', size=(70, 30))
        btn3.SetForegroundColour('yellow')
        btn3.SetBackgroundColour('black')
        hbox4.Add(btn3, border=10)

        vbox.Add(hbox4, flag=wx.ALIGN_RIGHT | wx.ALL, border=5)
        vbox.Add((-1, 5))

        self.SetSizer(vbox)

        # Config choices events
        self.Bind(wx.EVT_CHOICE, self.OnPortOpen, self.cboSpeed)
        self.Bind(wx.EVT_CHOICE, self.OnPortOpen, self.cboCPort)
        self.Bind(wx.EVT_CHOICE, self.OnTermType, self.cboTMode)
        self.Bind(wx.EVT_CHOICE, self.OnNewLine, self.cboNLine)
        self.Bind(wx.EVT_CHOICE, self.OnLocalEcho, self.choLEcho)

        self.txtTerm.Bind(wx.EVT_CHAR, self.OnTermChar)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(EVT_UPDATE_COMDATA, self.OnUpdateComData)
        self.Bind(EVT_UPDATE_COMMSG, self.OnUpdateComMsg)

        # Control  buttons Events objects
        btn1.Bind(wx.EVT_BUTTON, self.OnFileSave)
        btn2.Bind(wx.EVT_BUTTON, self.OnTermClear)
        btn3.Bind(wx.EVT_BUTTON, self.OnAbout)
        btn4.Bind(wx.EVT_BUTTON, self.OnDataReset)

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

        # terminal type[ASCI,HEX...]
        self.termType = self.cboTMode.GetStringSelection()

        # rx only setting
        self.rxOnly = False

        # newline character
        if 'CR' in self.cboNLine.GetStringSelection():
            self.newLine = 0x0D
        else:
            self.newLine = 0x0A

        # local echo
        self.localEcho = False

        # counter for alignment of hex display
        self.binCounter = 0

    # Clear terminal. Note that the raw data is not affected.
    def ClearTerminal(self):
        self.txtTerm.Clear()

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
        dout= self.rawdata.hex(':')
        f = open(data_file, 'wb')
        pickle.dump(dout, f)
        f.close()

    # Send data via COM port
    def SendData(self, data):
        if self.ser.is_open:
            self.ser.write(data)

    # Set new line character
    def SetNewLine(self, nl):
        if nl == 0x0D or nl == 0x0A:
            self.newLine = nl

    # Enable/disable local echo
    def SetLocalEcho(self, flag):
        self.localEcho = flag

    def SetRxOnly(self, flag=True):
        self.rxOnly = flag

    # Set terminal type
    def SetTermType(self, termtype):
        if termtype != '':
            self.termType = termtype

        if self.termType == 'Hex':
            self.txtTerm.AppendText('\n')
            self.binCounter = 0

    # Show/hide controls
    def ShowControls(self, flag):
        self.pnlControl.Show(flag)
        self.Layout()

    # Save file button handler
    def OnFileSave(self, evt):
        self.SaveRawData(data_file)

    # Clear terminal button handler
    def OnTermClear(self, evt):
        self.ClearTerminal()

    # Reset data button handler
    def OnDataReset(self, evt):
        self.ResetData()

    # Terminal type choice contrl handler
    def OnTermType(self, evt):
        # terminal type
        self.SetTermType(self.cboTMode.GetStringSelection())

    # Newline character choice control handler
    def OnNewLine(self, evt):
        if 'CR' in self.cboNLine.GetStringSelection():
            self.SetNewLine(0x0d)
        else:
            self.SetNewLine(0x0a)

    # Local echo mode selection handler
    def OnLocalEcho(self, evt):
        if 'Yes' in self.choLEcho.GetStringSelection():
            self.SetLocalEcho(True)
        else:
            self.SetLocalEcho(False)

    # Port selection choice handler
    def OnPortOpen(self, evt):
        port = self.cboCPort.GetStringSelection()
        speed = self.cboSpeed.GetStringSelection()

        # device is not selected
        if port == '':
            return

        # open the com port
        if self.OpenPort(port, speed):
            wx.MessageBox(port + ' is (re)open')
        else:
            wx.MessageBox('Failed to open: ' + port)

    # Terminal input handler
    def OnTermChar(self, evt):
        # no tx data if rxOnly
        if self.rxOnly:
            return

        if self.ser.is_open:
            # key code can be multiple bytes
            try:
                self.ser.write([evt.GetKeyCode()])
            except:
                pass

        if self.localEcho:
            if self.termType == 'ASCII':
                self.txtTerm.AppendText(chr(evt.GetKeyCode()))
            else:
                self.txtTerm.AppendText('0x{:02X}.'.format(evt.GetKeyCode()))

    # Local echo mode selection handler
    def OnSendPacket(self, evt):
        if self.ser.is_open:
            self.ser.write(OutPackets[self.choSndPkt.GetStringSelection()])

    # COM data input handler
    def OnUpdateComMsg(self, msg):
        self.rawdata2 = msg.data if isinstance(
            msg.data, bytearray) else bytearray(msg.data)
        dd= self.rawdata2.hex(':')
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
                self.ang = "XX"
            wx.PostEvent(self.parent, UpdateAngle(data=self.ang))
            #print(self.ang)
            
            # text display angel
            self.data1.Clear()
            self.data1.AppendText(self.ang)
            
                        
            #decode freq and laser thread type 
            s= dd[24]+dd[25]+dd[21]+dd[22]+dd[18]+dd[19]+dd[15]+dd[16]
            counts = int(s, 16)
            counts_time= counts*(20/(10**9))
            # dispaly count time
            hz= 1/counts_time
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
            self.tt= str(tms)
            self.data2.Clear()
            self.data2.AppendText(self.tt)
            self.data3.Clear()
            self.data3.AppendText(self.freq)
            self.data4.Clear()
            self.data4.AppendText(self.type)
            

            self.rawdata2 = bytearray()            
            dd = ''
        

    def OnUpdateComData(self, evt):

        for byte in evt.data :
            self.rawdata.append(byte)


            #return self.ang
            # time.sleep(1)
            # self.ResetData()

        for byte in evt.data:
            if self.termType == 'Protocol':
                # pass byte to the packet decoder
                ret = self.pd.AddByte(byte)
                # display packet decode result
                if ret is None:
                    pass
                else:
                    self.txtTerm.AppendText(ret + '\n')

            elif self.termType == 'Hex':
                # display formatted hex
                self.txtTerm.AppendText('0x{:02X}'.format(byte))
                # counter for alignment of the hex display
                self.binCounter = self.binCounter + 1

                if self.binCounter == 8:
                    self.txtTerm.AppendText(' - ')

                elif self.binCounter == 16:
                    self.txtTerm.AppendText('\n')
                    self.binCounter = 0

                else:
                    self.txtTerm.AppendText('.')

            else:
                if self.newLine == 0x0A:
                    if byte == 0x0D:
                        pass
                    elif byte == 0x0A:
                        self.txtTerm.AppendText('\n')
                    else:
                        self.txtTerm.AppendText(chr(byte))
                elif self.newLine == 0x0D:
                    if byte == 0x0A:
                        pass
                    elif byte == 0x0D:
                        self.txtTerm.AppendText('\n')
                    else:
                        self.txtTerm.AppendText(chr(byte))

        # self.ResetData()


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
        info.SetIcon(wx.Icon('logo.png', wx.BITMAP_TYPE_PNG))
        info.SetName('LWR Tracker')
        info.SetVersion('1.0')
        info.SetDescription(description)
        info.SetLicence(licence)
        info.SetCopyright('(C) 2011 - 2020 ')
        info.AddDeveloper('Infinity Tech Ltd')
        info.AddDocWriter('Technical Research Center of Egyption Armed Forces')
        info.SetWebSite('https://infinitytech.ltd')
        wx.adv.AboutBox(info)

 # ===========================================================================
 # Adding Panels to the main frame using Splitter
 # ===========================================================================


class LwrFrame(wx.Frame):

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent=None, title="LWR Tracker ")
     # serial terminal panel
        self.pnlTerm = ConPanel(self, serial.Serial(
            '/dev/pts/16'), size=(450, 300))
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
