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
import base64
import os
import subprocess
import sys
import socket
from itertools import cycle

from flask import Flask, render_template_string
from flask_socketio import SocketIO
from threading import Thread

import pyqrcode


try:
    from topdon.video import *
except:
    from video import *
    
    
class ThermalCamera:
    def __init__(self, **kwargs):
        self.config =       {
                            'web': False,
                            'port' : 5001,
                            }
        self.config.update(kwargs)
        self.videostore = Video()
        self.web = self.config['web']
        self.width = 256  # Sensor width
        self.height = 192  # sensor height
        self.scale = 3  # scale multiplier
        self.newWidth = self.width * self.scale
        self.newHeight = self.height * self.scale
        self.alpha = 1.0  # Contrast control (1.0-3.0)
        
        self.colormap_options = cycle(list(range(11)))
        self.colormap = next(self.colormap_options)
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        
        self.dispFullscreen_options = cycle([False,True])
        self.dispFullscreen = next(self.dispFullscreen_options)
        
        self.rad = 0  # blur radius
        self.threshold = 2
        self.hud_options = cycle(['all','cross','spots','none'])
        self.hud = next(self.hud_options)
        
        self.recording_options = cycle([False,True])
        self.recording = next(self.recording_options)
        
        self.elapsed = "00:00:00"
        self.snaptime = "None"
        
        if self.web == True:
            self.init_webapp()
            self.video_thread = Thread(target=lambda: self.app.run(debug=False, port=self.config['port'], threaded=True, host='0.0.0.0'))
            self.video_thread.start()
            ip_adress = self.get_ip_address()
            url = f'http://{ip_adress}:{self.config["port"]}'
            url_qr = pyqrcode.create(url).terminal(module_color='white', background='black')
            print(f'############################\n\nOpen: {url}\n{url_qr}\n\n############################')
            self.open_port()
            
    def get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address
        except:
            return '127.0.0.1'
            
    def init_webapp(self):
        app = Flask('Video Stream')
        app.current_frame = None
        app.index_string = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Stream</title>
</head>
<style>
    body, html {
        margin: 0;
        padding: 0;
        height: 100%;
        overflow: hidden;
    }

    #videoFrame {
        object-fit: contain;
        width: 100%;
        height: 100vh;
    }
</style>
<body>
    <img id="videoFrame">

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        var socket = io.connect('http://' + document.domain + ':' + location.port);

        socket.on('update_frame', function(data) {
            document.getElementById('videoFrame').src = 'data:image/jpeg;base64,' + data.current_frame;
        });
    </script>
</body>
</html>
        """  
        
        @app.route('/')
        def index():
            return render_template_string(app.index_string, current_frame=app.current_frame)
        
        self.app = app
        self.socket = SocketIO(self.app)
        
    def update_web_frame(self,frame):
        _, buffer = cv2.imencode('.jpg', frame)
        self.app.current_frame = base64.b64encode(buffer).decode('utf-8')
        self.socket.emit('update_frame', {'current_frame': self.app.current_frame})
        
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

    def _compute_temperature(self, data):
        hi = data[96][128][0]
        lo = data[96][128][1]
        lo = lo * 256
        rawtemp = hi + lo
        temp = (rawtemp / 64) - 273.15
        return round(temp, 2)

    def _process_frame(self, frame):
        # now parse the data from the bottom frame and convert to temp!
        # https://www.eevblog.com/forum/thermal-imaging/infiray-and-their-p2-pro-discussion/200/
        # Huge props to LeoDJ for figuring out how the data is stored and how to compute temp from it.
        imdata, thdata = np.array_split(frame, 2)

        temp = self._compute_temperature(thdata)

        # Find the max temperature in the frame
        lomax = thdata[..., 1].max()
        posmax = thdata[..., 1].argmax()
        mcol, mrow = divmod(posmax, self.width)
        himax = thdata[mcol][mrow][0]
        lomax = lomax * 256
        maxtemp = (himax + lomax) / 64 - 273.15
        maxtemp = round(maxtemp, 2)

        # Find the lowest temperature in the frame
        lomin = thdata[..., 1].min()
        posmin = thdata[..., 1].argmin()
        lcol, lrow = divmod(posmin, self.width)
        himin = thdata[lcol][lrow][0]
        lomin = lomin * 256
        mintemp = (himin + lomin) / 64 - 273.15
        mintemp = round(mintemp, 2)

        # Find the average temperature in the frame
        loavg = thdata[..., 1].mean()
        hiavg = thdata[..., 0].mean()
        loavg = loavg * 256
        avgtemp = (hiavg + loavg) / 64 - 273.15
        avgtemp = round(avgtemp, 2)

        return temp, maxtemp, mintemp, avgtemp, imdata, thdata, mcol, mrow, lcol, lrow

    def run(self):
        self.videostore.open()
        self.cap = self.videostore.cap

        self.init_windows()
        self.print_thermal_camera_info()
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret == True:                         
                temp, maxtemp, mintemp, avgtemp, imdata, thdata, mcol, mrow, lcol, lrow = self._process_frame(frame)
                          
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
                          
                          
                if (self.hud=='all') or (self.hud=='cross'):
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
                          
                if self.hud=='all':
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
                
                if (self.hud!='none'):
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
                if self.web:
                    self.update_web_frame(heatmap)
                          
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
                          
                if keyPress == ord('w'): #toggle fullscreen
                    self.dispFullscreen = next(self.dispFullscreen_options)

                    if self.dispFullscreen==True:
                        cv2.namedWindow('Thermal',cv2.WND_PROP_FULLSCREEN)
                        cv2.setWindowProperty('Thermal',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
                    elif self.dispFullscreen==False:
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
                          
                          
                if keyPress == ord('h'): # cycle through hud options
                    self.hud = next(self.hud_options)
                          
                if keyPress == ord('m'): #m to cycle through color maps
                    self.colormap = next(self.colormap_options)
                          
                if keyPress == ord('r'):
                    self.recording = next(self.recording_options)

                    if self.recording == True:
                        videoOut = self.rec()
                        start = time.time()
                    else:
                        self.elapsed = "00:00:00"
                          
                if keyPress == ord('p'):
                    self.snapshot(heatmap)
                          
                if keyPress == ord('q'):
                    self.cap.release()
                    cv2.destroyAllWindows()
                    self.__del__()
                    break

                    
    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
            
        if self.web == True:
            try:
                self.close_port()
                if self.video_thread.is_alive():
                    self.video_thread.terminate()
                    self.video_thread.join()
            except: pass

    def check_sudo(self):
        try:
            subprocess.run(['sudo', '-n', 'ls'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def open_port(self):
        if self.check_sudo():
            try:
                os.system(f'sudo ufw allow {self.config["port"]}')
                print(f'Port {self.config["port"]} erfolgreich geöffnet.')
            except Exception as e:
                print(f'Fehler beim Öffnen des Ports {self.config["port"]}: {e}')
    
    def close_port(self):
        if self.check_sudo():
            try:
                os.system(f'sudo ufw delete allow {self.config["port"]}')
                print(f'Port {self.config["port"]} erfolgreich geschlossen.')
            except Exception as e:
                print(f'Fehler beim Schließen des Ports {self.config["port"]}: {e}')
                    
    def print_thermal_camera_info(self):
        info = """
LMH
(from https://github.com/leswright1977/PyThermalCamera )

Key Bindings:

a z     : Increase/Decrease Blur
s x     : Floating High and Low Temp Label Threshold
d c     : Change Interpolated scale
f v     : Contrast
w       : Toggle Fullscreen / Windowed
r       : Start and stop recording
p       : Snapshot photo
m       : Cycle through ColorMaps
h       : Toggle HUD
"""
        print(info)
        
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Thermal Camera')
    
    parser.add_argument('--web', action='store_true', help='Starte die ThermalCamera mit Webunterstützung')
    parser.add_argument('--port', type=int, default=5001, help='Der Port für die Webunterstützung (Standard: 5001)')

    args = parser.parse_args()
        
    self = ThermalCamera(**vars(args))
    self.run()

if __name__ == "__main__":
    self = ThermalCamera()
    self.run()