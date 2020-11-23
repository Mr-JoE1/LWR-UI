#!/usr/bin/env python3

import _thread
import sys
import math
import serial
import wx
import wx.lib.newevent


# import ComThread and TermPanel
from termpn import *

class RadarGraph(wx.Panel):

    def __init__(self, parent, title, labels, **kwgs):
        wx.Panel.__init__(self, parent, size=(450,350), **kwgs )
        self.SetBackgroundColour('WHITE')
        self.title = title
        self.labels = labels
        self.data = [0.0] * len(labels)
        self.titleFont = wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.labelFont = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
                

        self.InitBuffer()

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)


    def OnSize(self, evt):
        # When the window size changes we need a new buffer.
        self.InitBuffer()


    def OnPaint(self, evt):
        # This automatically Blits self.buffer to a wx.PaintDC when
        # the dc is destroyed, and so nothing else needs done.
        dc = wx.BufferedPaintDC(self, self.buffer)


    def InitBuffer(self):
        # Create the buffer bitmap to be the same size as the window,
        # then draw our graph to it.  Since we use wx.BufferedDC
        # whatever is drawn to the buffer is also drawn to the window.
        w, h = self.GetClientSize()        
        self.buffer = wx.Bitmap(w, h)
        dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)
        self.DrawGraph(dc)
        
    def PolarToCartesian(self, radius, angle, cx, cy):
        x = radius * math.cos(math.radians(angle))
        y = radius * math.sin(math.radians(angle))
        return (cx+x, cy-y)
    
    # thread angle decoding function-- ang must rutuned from SericalCom.py     
    def ThreadAngle(self, rad, ang, cx, cy):
        yy = rad * math.cos(math.radians(ang))
        xx = rad * math.sin(math.radians(ang))   
        print(rad ,cx , cy )
        
        return (cx+xx, cy-yy)

    def DrawGraph(self, dc):
        spacer = 10
        scaledmax = 130.0

        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()
        dw, dh = dc.GetSize()

        # Find out where to draw the title and do it
        dc.SetFont(self.titleFont)
        tw, th = dc.GetTextExtent(self.title)
        #dc.DrawText(self.title, int((dw-tw)/2), spacer)

        # find the center of the space below the title
        th = th + 2*spacer
        cx = int(dw/2)
        cy = int((dh-th)/2) + th 

        # calculate a scale factor to use for drawing the graph based
        # on the minimum available width or height
        mindim = min(cx, (dh-th)/2)
        scale = mindim/scaledmax

        # draw the graph axis and "bulls-eye" with rings at scaled 25,
        # 50, 75 and 100 positions
        dc.SetPen(wx.Pen('blue', 2))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawCircle(cx,cy, int(25*scale))
        dc.DrawCircle(cx,cy, int(50*scale))
        dc.DrawCircle(cx,cy, int(75*scale))
        dc.DrawCircle(cx,cy, int(100*scale))

        dc.SetPen(wx.Pen('black', 2))
        dc.DrawLine(int(cx-110*scale), cy, int(cx+110*scale), cy)
        dc.DrawLine(cx, int(cy-110*scale), cx, int(cy+110*scale))
        dc.SetPen(wx.Pen('red', 3))

       
        xx, yy= self.ThreadAngle(115*scale, 45 , cx, cy)
        dc.DrawLine(cx, cy, int(xx), int(yy))
        print(scale)
        
        # Now find the coordinates for each data point, draw the
        # labels, and find the max data point
        dc.SetFont(self.labelFont)
        maxval = 0
        angle = 0
        polypoints = []
        for i, label in enumerate(self.labels):
            val = self.data[i]
            point = self.PolarToCartesian(val*scale, angle, cx, cy)
            polypoints.append(point)
            x, y = self.PolarToCartesian(115*scale, angle, cx,cy)
            dc.DrawText(label, int(x), int(y))
            if val > maxval:
                maxval = val
            angle = angle + 360/len(self.labels)
            
            


class MyFrame(wx.Frame):

    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER, size=(450, 650))
        
        # Add window icon
        icons = wx.IconBundle()
        #icons.AddIconFromFile(self._get_img_path('logo.ico'), wx.BITMAP_TYPE_ANY)
        icons.AddIcon(wx.Icon('logo.ico'))
        self.SetIcons(icons)
        
        
        # populate two terminal panels
        self.pnlTerm1 = RadarGraph(self, "",
                          ["يميني", "45", "أمامي", "315", "يساري", "225", "خلفي", "135"] )
        self.pnlTerm2 =  ConPanel(self, serial.Serial() )

        # set RX only mode
        self.pnlTerm2.SetRxOnly()

        # sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.pnlTerm1, 1, wx.EXPAND)
        self.sizer.Add(self.pnlTerm2, 1, wx.EXPAND)

        self.SetSizer(self.sizer)
        self.Show()


#--------1---------2---------3---------4---------5---------6---------7---------8
if __name__=="__main__":

    app = wx.App()
    frame = MyFrame(None, "LWR Tracker")
    app.MainLoop()
