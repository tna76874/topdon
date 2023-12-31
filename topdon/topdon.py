#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
LMH 31.12.2023

from:
Les Wright 21 June 2023
https://youtube.com/leslaboratory
A Python program to read, parse and display thermal data from the Topdon TC001 Thermal camera!
https://github.com/leswright1977/PyThermalCamera
'''
import cv2
import numpy as np
import argparse
import time
import io

try:
    from topdon.video import *
except:
    from video import *

class ThermalCamera:
    def __init__(self):
        self.videostore = Video()
        self.width = 256  # Sensor width
        self.height = 192  # sensor height
        self.scale = 3  # scale multiplier
        self.newWidth = self.width * self.scale
        self.newHeight = self.height * self.scale
        self.alpha = 1.0  # Contrast control (1.0-3.0)
        self.colormap = 0
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.dispFullscreen = False
        self.rad = 0  # blur radius
        self.threshold = 2
        self.hud = True
        self.recording = False
        self.elapsed = "00:00:00"
        self.snaptime = "None"
        
    def init_windows(self):
        cv2.namedWindow('Thermal', cv2.WINDOW_GUI_NORMAL)
        cv2.resizeWindow('Thermal', self.newWidth, self.newHeight)        

    def rec(self):
        now = time.strftime("%Y%m%d--%H%M%S")
        videoOut = cv2.VideoWriter(
            now + 'output.avi', cv2.VideoWriter_fourcc(*'XVID'), 25, (self.newWidth, self.newHeight)
        )
        return videoOut

    def snapshot(self, heatmap):
        now = time.strftime("%Y%m%d-%H%M%S")
        self.snaptime = time.strftime("%H:%M:%S")
        cv2.imwrite("TC001" + now + ".png", heatmap)

    def run(self):
        self.videostore.open()
        self.cap = self.videostore.cap

        self.init_windows()
        self.print_thermal_camera_info()
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret == True:
                imdata,thdata = np.array_split(frame, 2)
                #now parse the data from the bottom frame and convert to temp!
                #https://www.eevblog.com/forum/thermal-imaging/infiray-and-their-p2-pro-discussion/200/
                #Huge props to LeoDJ for figuring out how the data is stored and how to compute temp from it.
                #grab data from the center pixel...
                hi = thdata[96][128][0]
                lo = thdata[96][128][1]
                #print(hi,lo)
                lo = lo*256
                rawtemp = hi+lo
                #print(rawtemp)
                temp = (rawtemp/64)-273.15
                temp = round(temp,2)
                #print(temp)
                #break
                          
                #find the max temperature in the frame
                lomax = thdata[...,1].max()
                posmax = thdata[...,1].argmax()
                #since argmax returns a linear index, convert back to row and col
                mcol,mrow = divmod(posmax,self.width)
                himax = thdata[mcol][mrow][0]
                lomax=lomax*256
                maxtemp = himax+lomax
                maxtemp = (maxtemp/64)-273.15
                maxtemp = round(maxtemp,2)
                          
                
                #find the lowest temperature in the frame
                lomin = thdata[...,1].min()
                posmin = thdata[...,1].argmin()
                #since argmax returns a linear index, convert back to row and col
                lcol,lrow = divmod(posmin,self.width)
                himin = thdata[lcol][lrow][0]
                lomin=lomin*256
                mintemp = himin+lomin
                mintemp = (mintemp/64)-273.15
                mintemp = round(mintemp,2)
                          
                #find the average temperature in the frame
                loavg = thdata[...,1].mean()
                hiavg = thdata[...,0].mean()
                loavg=loavg*256
                avgtemp = loavg+hiavg
                avgtemp = (avgtemp/64)-273.15
                avgtemp = round(avgtemp,2)
                          
                
                          
                # Convert the real image to RGB
                bgr = cv2.cvtColor(imdata,  cv2.COLOR_YUV2BGR_YUYV)
                #Contrast
                bgr = cv2.convertScaleAbs(bgr, alpha=self.alpha)#Contrast
                #bicubic interpolate, upscale and blur
                bgr = cv2.resize(bgr,(self.newWidth,self.newHeight),interpolation=cv2.INTER_CUBIC)#Scale up!
                if self.rad>0:
                    bgr = cv2.blur(bgr,(self.rad,self.rad))
                          
                #apply colormap
                if self.colormap == 0:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_JET)
                    cmapText = 'Jet'
                if self.colormap == 1:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_HOT)
                    cmapText = 'Hot'
                if self.colormap == 2:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_MAGMA)
                    cmapText = 'Magma'
                if self.colormap == 3:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_INFERNO)
                    cmapText = 'Inferno'
                if self.colormap == 4:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_PLASMA)
                    cmapText = 'Plasma'
                if self.colormap == 5:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_BONE)
                    cmapText = 'Bone'
                if self.colormap == 6:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_SPRING)
                    cmapText = 'Spring'
                if self.colormap == 7:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_AUTUMN)
                    cmapText = 'Autumn'
                if self.colormap == 8:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_VIRIDIS)
                    cmapText = 'Viridis'
                if self.colormap == 9:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_PARULA)
                    cmapText = 'Parula'
                if self.colormap == 10:
                    heatmap = cv2.applyColorMap(bgr, cv2.COLORMAP_RAINBOW)
                    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
                    cmapText = 'Inv Rainbow'
                          
                #print(heatmap.shape)
                          
                # draw crosshairs
                cv2.line(heatmap,(int(self.newWidth/2),int(self.newHeight/2)+20),\
                (int(self.newWidth/2),int(self.newHeight/2)-20),(255,255,255),2) #vline
                cv2.line(heatmap,(int(self.newWidth/2)+20,int(self.newHeight/2)),\
                (int(self.newWidth/2)-20,int(self.newHeight/2)),(255,255,255),2) #hline
                          
                cv2.line(heatmap,(int(self.newWidth/2),int(self.newHeight/2)+20),\
                (int(self.newWidth/2),int(self.newHeight/2)-20),(0,0,0),1) #vline
                cv2.line(heatmap,(int(self.newWidth/2)+20,int(self.newHeight/2)),\
                (int(self.newWidth/2)-20,int(self.newHeight/2)),(0,0,0),1) #hline
                #show temp
                cv2.putText(heatmap,str(temp)+' C', (int(self.newWidth/2)+10, int(self.newHeight/2)-10),\
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(heatmap,str(temp)+' C', (int(self.newWidth/2)+10, int(self.newHeight/2)-10),\
                cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0, 255, 255), 1, cv2.LINE_AA)
                          
                if self.hud==True:
                    # display black box for our data
                    cv2.rectangle(heatmap, (0, 0),(160, 120), (0,0,0), -1)
                    # put text in the box
                    cv2.putText(heatmap,'Avg Temp: '+str(avgtemp)+' C', (10, 14),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)
                          
                    cv2.putText(heatmap,'Label Threshold: '+str(self.threshold)+' C', (10, 28),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)
                          
                    cv2.putText(heatmap,'Colormap: '+cmapText, (10, 42),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)
                          
                    cv2.putText(heatmap,'Blur: '+str(self.rad)+' ', (10, 56),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)
                          
                    cv2.putText(heatmap,'Scaling: '+str(self.scale)+' ', (10, 70),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)
                          
                    cv2.putText(heatmap,'Contrast: '+str(self.alpha)+' ', (10, 84),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)
                          
                          
                    cv2.putText(heatmap,'Snapshot: '+self.snaptime+' ', (10, 98),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)
                          
                    if self.recording == False:
                    	cv2.putText(heatmap,'Recording: '+self.elapsed, (10, 112),\
                    	cv2.FONT_HERSHEY_SIMPLEX, 0.4,(200, 200, 200), 1, cv2.LINE_AA)
                    if self.recording == True:
                    	cv2.putText(heatmap,'Recording: '+self.elapsed, (10, 112),\
                    	cv2.FONT_HERSHEY_SIMPLEX, 0.4,(40, 40, 255), 1, cv2.LINE_AA)
                
                #Yeah, this looks like we can probably do this next bit more efficiently!
                #display floating max temp
                if maxtemp > avgtemp+self.threshold:
                    cv2.circle(heatmap, (mrow*self.scale, mcol*self.scale), 5, (0,0,0), 2)
                    cv2.circle(heatmap, (mrow*self.scale, mcol*self.scale), 5, (0,0,255), -1)
                    cv2.putText(heatmap,str(maxtemp)+' C', ((mrow*self.scale)+10, (mcol*self.scale)+5),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0,0,0), 2, cv2.LINE_AA)
                    cv2.putText(heatmap,str(maxtemp)+' C', ((mrow*self.scale)+10, (mcol*self.scale)+5),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0, 255, 255), 1, cv2.LINE_AA)
                          
                #display floating min temp
                if mintemp < avgtemp-self.threshold:
                    cv2.circle(heatmap, (lrow*self.scale, lcol*self.scale), 5, (0,0,0), 2)
                    cv2.circle(heatmap, (lrow*self.scale, lcol*self.scale), 5, (255,0,0), -1)
                    cv2.putText(heatmap,str(mintemp)+' C', ((lrow*self.scale)+10, (lcol*self.scale)+5),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0,0,0), 2, cv2.LINE_AA)
                    cv2.putText(heatmap,str(mintemp)+' C', ((lrow*self.scale)+10, (lcol*self.scale)+5),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,(0, 255, 255), 1, cv2.LINE_AA)
                          
                #display image
                cv2.imshow('Thermal',heatmap)
                          
                if self.recording == True:
                    self.elapsed = (time.time() - start)
                    self.elapsed = time.strftime("%H:%M:%S", time.gmtime(self.elapsed)) 
                    #print(elapsed)
                    videoOut.write(heatmap)
                
                keyPress = cv2.waitKey(1)
                if keyPress == ord('a'): #Increase blur radius
                    self.rad += 1
                if keyPress == ord('z'): #Decrease blur radius
                    self.rad -= 1
                    if self.rad <= 0:
                    	self.rad = 0
                          
                if keyPress == ord('s'): #Increase threshold
                    self.threshold += 1
                if keyPress == ord('x'): #Decrease threashold
                    self.threshold -= 1
                    if self.threshold <= 0:
                    	self.threshold = 0
                          
                if keyPress == ord('d'): #Increase scale
                    self.scale += 1
                    if self.scale >=5:
                    	self.scale = 5
                    self.newWidth = self.width*self.scale
                    self.newHeight = self.height*self.scale
                    if self.dispFullscreen == False:
                    	cv2.resizeWindow('Thermal', self.newWidth,self.newHeight)
                if keyPress == ord('c'): #Decrease scale
                    self.scale -= 1
                    if self.scale <= 1:
                    	self.scale = 1
                    self.newWidth = self.width*self.scale
                    self.newHeight = self.height*self.scale
                    if self.dispFullscreen == False:
                    	cv2.resizeWindow('Thermal', self.newWidth,self.newHeight)
                          
                if keyPress == ord('q'): #enable fullscreen
                    self.dispFullscreen = True
                    cv2.namedWindow('Thermal',cv2.WND_PROP_FULLSCREEN)
                    cv2.setWindowProperty('Thermal',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
                if keyPress == ord('w'): #disable fullscreen
                    self.dispFullscreen = False
                    cv2.namedWindow('Thermal',cv2.WINDOW_GUI_NORMAL)
                    cv2.setWindowProperty('Thermal',cv2.WND_PROP_AUTOSIZE,cv2.WINDOW_GUI_NORMAL)
                    cv2.resizeWindow('Thermal', self.newWidth,self.newHeight)
                          
                if keyPress == ord('f'): #contrast+
                    self.alpha += 0.1
                    self.alpha = round(self.alpha,1)#fix round error
                    if self.alpha >= 3.0:
                    	self.alpha=3.0
                if keyPress == ord('v'): #contrast-
                    self.alpha -= 0.1
                    self.alpha = round(self.alpha,1)#fix round error
                    if self.alpha<=0:
                    	self.alpha = 0.0
                          
                          
                if keyPress == ord('h'):
                    if self.hud==True:
                    	self.hud=False
                    elif self.hud==False:
                    	self.hud=True
                          
                if keyPress == ord('m'): #m to cycle through color maps
                    self.colormap += 1
                    if self.colormap == 11:
                    	self.colormap = 0
                          
                if keyPress == ord('r') and self.recording == False: #r to start reording
                    videoOut = self.rec()
                    self.recording = True
                    start = time.time()
                if keyPress == ord('t'): #f to finish reording
                    self.recording = False
                    self.elapsed = "00:00:00"
                          
                if keyPress == ord('p'): #f to finish reording
                    self.snapshot(heatmap)
                          
                if keyPress == ord('q'):
                    self.cap.release()
                    cv2.destroyAllWindows()
                    break

                    
    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
                    
    def print_thermal_camera_info(self):
        info = """
LMH
(from https://github.com/leswright1977/PyThermalCamera )

Key Bindings:

a z: Increase/Decrease Blur
s x: Floating High and Low Temp Label Threshold
d c: Change Interpolated scale
f v: Contrast
q w: Fullscreen Windowed
r t: Record and Stop
p : Snapshot
m : Cycle through ColorMaps
h : Toggle HUD
"""
        print(info)
        
def main():
    self = ThermalCamera()
    self.run()   

if __name__ == "__main__":
    self = ThermalCamera()
    # self.run()
