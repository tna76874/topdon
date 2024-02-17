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
import pandas as pd
import argparse
import time
from datetime import datetime
import io
import base64
import os
import subprocess
import sys
import socket
from itertools import cycle

from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO
from threading import Thread

import pyqrcode

import logging

from quickflare.quickflare import CloudflaredManager

logging.getLogger('werkzeug').setLevel(logging.ERROR)

try:
    from topdon.video import *
    from topdon.updater import *
except:
    from video import *
    from updater import *
    
current_dir = os.path.dirname(os.path.abspath(__file__))
template_folder = os.path.join(current_dir, 'templates')
static_folder = os.path.join(current_dir, 'static')

class ThermalFrame:
    def __init__(self, camera, frame, rnd = 2):
        self.imdata, self.thdata = np.array_split(frame, 2)
        self.rnd = rnd
        self.camera=camera
        self.height, self.width, _ = self.imdata.shape

    def rotate(self, rotation):
        self.imdata = cv2.rotate(self.imdata, rotation)
        self.thdata = cv2.rotate(self.thdata, rotation)
        self.height, self.width, _ = self.imdata.shape

    def flip(self):
        self.imdata = cv2.flip(self.imdata, 1)
        self.thdata = cv2.flip(self.thdata, 1)

    def _set_target(self,h,w):
        self.target_h = int(h)
        self.target_w = int(w)
        self.target_temp = np.round(self.temperatures[self.target_h][self.target_w],self.rnd)

    def _convert_raw_temp_data_to_kelvin_topdon(self, thdata):
        """
        thdata[..., 1] contains just some offset/calibration in the range about 300 K
        thdata[..., 0] contains a little temp offset
        ... /64 is equivalent to the bitshift operation >> 6. This way, the temperature is only encoded via integer numbers.
        """
        return (thdata[..., 0] + thdata[..., 1] * 256) / 64

    def _get_celsius_temperatures(self):
        return self._convert_raw_temp_data_to_kelvin_topdon(self.thdata) - 273.15

    def _process_frame(self):
        # converting kelvon to celsius
        if self.camera['name'] == 'TC001':
            self.temperatures = self._get_celsius_temperatures()
        else:
            raise Exception('Unknown camera')
        
    
        self.maxtemp, self.mintemp, self.avgtemp = [np.round(k,self.rnd) for k in [self.temperatures.max(), self.temperatures.min(), self.temperatures.mean()]]

    def _get_data(self, newWidth):
        self.maxtemp_index = divmod(self.temperatures.argmax(), self.width)
        self.mintemp_index = divmod(self.temperatures.argmin(), self.width)
        
        img_data = {
                'avg_temp': self.avgtemp,
                'max_temp': self.maxtemp,
                'min_temp': self.mintemp,
                'target_temp'    : self.target_temp,
                'max_temp_x': int(self.maxtemp_index[0]*newWidth/self.width),
                'max_temp_y': int(self.maxtemp_index[1]*newWidth/self.width),
                'min_temp_x': int(self.mintemp_index[0]*newWidth/self.width),
                'min_temp_y': int(self.mintemp_index[1]*newWidth/self.width),
                'target_x': int(self.target_h*newWidth/self.width),
                'target_y': int(self.target_w*newWidth/self.width),
            }
        return img_data


class PhotoSnapshot:
    def __init__(self, camera, imdata, temperatures, img_data):
        self.camera = camera.copy()
        self.imdata = imdata
        self.thdata = temperatures
        self.data = img_data
        self.init_t = datetime.now()
        
        self.save_to_xlsx()
        self.save_image()

    def _time_str(self):
        return self.init_t.strftime("%Y%m%d-%H%M%S")
    
    def save_to_xlsx(self):
        xlsx_file = f'{self.camera["name"]}_{self._time_str()}.xlsx'
        DF_temp = pd.DataFrame(self.thdata)
        DF_temp.index += 1
        DF_temp.columns += 1
        
        DF_data = pd.DataFrame([self.data])
        
        with pd.ExcelWriter(xlsx_file, engine='xlsxwriter') as writer:
            DF_data.to_excel(writer, sheet_name='Data', index=False)
            DF_temp.to_excel(writer, sheet_name='Temperatures', index=True)

        
    def save_image(self):
        cv2.imwrite(f'{self.camera["name"]}_{self._time_str()}.png', self.imdata)
    
class VideoRecorder:
    def __init__(self, camera, width, height):
        self.camera = camera.copy()
        self.width = width
        self.height = height
        self.init_t = datetime.now()
        self.data = list()

        self.video_out = self._initialize_video_out()

    def _time_str(self):
        return self.init_t.strftime("%Y%m%d-%H%M%S")

    def _initialize_video_out(self):
        file_name = f'{self.camera["name"]}_{self._time_str()}.avi'
        video_out = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*'XVID'), 25, (self.width, self.height))
        return video_out

    def add_frame(self, frame, data=None):
        self.video_out.write(frame)
        if data!=None:
            update_data = {'t':(datetime.now() - self.init_t).total_seconds()}
            update_data.update(data)
            self.data.append(update_data)
        
    def save_to_xlsx(self):
        xlsx_file = f'{self.camera["name"]}_{self._time_str()}.xlsx'
        DF_data = pd.DataFrame(self.data)
        DF_data.to_excel(xlsx_file, index=False)

    def release(self):
        self.video_out.release()

    def __del__(self):
        self.release()
        if len(self.data)!=0:
            self.save_to_xlsx()
    
class ThermalCamera:
    def __init__(self, **kwargs):
        self.config =       {
                            'web': True,
                            'port' : 5001,
                            'qt' : False,
                            'cf' : False,
                            'compress' : True,
                            'camera' : -1,
                            }
        self.config.update(kwargs)
        self.videostore = Video()
        self.web = self.config['web']
        self.width = 256  # Sensor width
        self.height = 192  # sensor height
        
        self.target_w = int(self.width/2)
        self.target_h = int(self.height/2)
        self.target = None
        
        self.targetstep = 1        
        
        self.scale = 3  # scale multiplier
        self.newWidth = self.width * self.scale
        self.newHeight = self.height * self.scale
        self.set_target_pos()
        self.alpha = 1.0  # Contrast control (1.0-3.0)
        
        self.colormap_options = cycle(list(range(11)))
        self.colormap = next(self.colormap_options)
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
 
        self.rotation_options = cycle([None,cv2.ROTATE_90_CLOCKWISE,cv2.ROTATE_180,cv2.ROTATE_90_COUNTERCLOCKWISE])
        self.rotation = next(self.rotation_options)       
 
        self.dispFullscreen_options = cycle([False,True])
        self.dispFullscreen = next(self.dispFullscreen_options)
        
        self.flip_options = cycle([False,True])
        self.flip = next(self.flip_options)
        
        self.rad = 0  # blur radius
        self.threshold = 2
        self.hud_options = cycle(['cross','spots','none','all'])
        self.hud = next(self.hud_options)
        
        self.recording_options = cycle([False,True])
        self.recording = next(self.recording_options)
        
        self.elapsed = "00:00:00"
        self.snaptime = "None"
        
        self.videoOut = None
        self.start = None
        
        self.isqt = not self.config['web'] or self.config['qt']
        
        self.heatmap = None
        self.thdata = None
        self.temp_unit = " C"

        if self.web == True:

            if (self.config['cf'] == True):
                self._init_cloudflared()
                
            # set websocket framerate for cloudflared
            self.target_fps = 10
            self.update_interval_seconds = 1 / self.target_fps
            self.last_update_time = datetime.now()
                
            self.init_webapp()
            self.video_thread = Thread(target=lambda: self.app.run(debug=False, port=self.config['port'], threaded=True, host='0.0.0.0', use_reloader=False))
            self.video_thread.setDaemon(True)
            self.video_thread.start()
            ip_adress = self.get_ip_address()
            if (self.config['cf'] == True):
                url = self.cf.tunnel_url
            else:
                url = f'http://{ip_adress}:{self.config["port"]}'

            url_qr = pyqrcode.create(url).terminal(module_color='white', background='black')
            print(f'############################\n\nOpen: {url}\n{url_qr}\n\n############################')
            print('\n\n ---> CTRL+C to quit')
            self.open_port()
            
    def _init_cloudflared(self):
        self.cf = CloudflaredManager(port=self.config['port'])
        self.cf.start(info=True)
            
    def set_target_pos(self):
        self.target = (int(self.newWidth * self.target_w / self.width), int(self.newHeight* self.target_h / self.height))

            
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
        app = Flask('Thermal Camera Viewer', template_folder=template_folder, static_folder=static_folder)
        app.current_frame = None
    
        @app.route('/scripts/<script_name>')
        def serve_script(script_name):
            return app.send_static_file(f'scripts/{script_name}')
        
        @app.route('/css/<path:css_path>')
        def serve_css(css_path):
            return app.send_static_file(os.path.join('css',css_path))
        
        @app.route('/')
        def index():
            return render_template('index.html', current_frame=app.current_frame, camera=self.videostore.camera)
        
        @app.route('/toggle_recording')
        def toggle_recording():
            self._toggle_recording()
            return ''
        
        @app.route('/cycle_hud')
        def cycle_hud():
            self._cycle_hud()
            return ''
        
        @app.route('/take_photo')
        def take_photo():
            self.snapshot()
            return ''
        
        @app.route('/rotate_image')
        def rotate_image():
            self._rotate_image()
            return ''
        
        @app.route('/flip_image')
        def flip_image():
            self._flip_image()
            return ''
        
        @app.route('/send_coordinates')
        def send_coordinates():
            y = float(request.args.get('x'))
            x = float(request.args.get('y'))
            
            self.target_h = int(x*self.height)
            self.target_w = int(y*self.width)
            self.set_target_pos()
            return ''
        
        
        self.app = app
        self.socket = SocketIO(self.app)

    def update_web_frame(self, frame, quality=50):
        current_time = datetime.now()
        time_difference = current_time - self.last_update_time
        
        if self.config['compress'] == True:
            if time_difference.total_seconds() >= self.update_interval_seconds:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                self.app.current_frame = base64.b64encode(buffer).decode('utf-8')
                self.socket.emit('update_frame', {'current_frame': self.app.current_frame, 'image_width': self.newWidth, 'image_height': self.newHeight})
                self.last_update_time = current_time
        else:
            _, buffer = cv2.imencode('.jpg', frame)
            self.app.current_frame = base64.b64encode(buffer).decode('utf-8')
            self.socket.emit('update_frame', {'current_frame': self.app.current_frame, 'image_width': self.newWidth, 'image_height': self.newHeight})


    def init_windows(self):
        if self.isqt:
            cv2.namedWindow('Thermal', cv2.WINDOW_GUI_NORMAL)
            cv2.resizeWindow('Thermal', self.newWidth, self.newHeight)
            
    def snapshot(self):       
        PhotoSnapshot(self.videostore.camera, self.heatmap, self.thdata, self.img_data)
        
    def run(self):
        try:
            self._run()
        except KeyboardInterrupt:
            print("Exiting . . .")
            sys.exit(0)

    def _run(self):
        self.videostore.open(camera_id=self.config['camera'])
        self.cap = self.videostore.cap

        self.init_windows()
        if self.isqt: self.print_thermal_camera_info()
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret == True:
                self.TFrame = ThermalFrame(self.videostore.camera, frame)
                
                if self.rotation!=None:
                    self.TFrame.rotate(self.rotation)
                    
                if self.flip:
                    self.TFrame.flip()
                    
                self.TFrame._process_frame()
                self.TFrame._set_target(self.target_h, self.target_w)
                
                self.thdata = self.TFrame.temperatures
                
                self.img_data = self.TFrame._get_data(self.newWidth)
                          
                # Convert the real image to RGB
                bgr = cv2.cvtColor(self.TFrame.imdata,  cv2.COLOR_YUV2BGR_YUYV)
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
                    center = self.target
                    
                    # Weiß gestrichelte Linien
                    cv2.line(heatmap, (center[0], center[1] + 20), (center[0], center[1] - 20), (255, 255, 255), 2)  # vline
                    cv2.line(heatmap, (center[0] + 20, center[1]), (center[0] - 20, center[1]), (255, 255, 255), 2)  # hline
                    
                    # Schwarze gestrichelte Linien
                    cv2.line(heatmap, (center[0], center[1] + 20), (center[0], center[1] - 20), (0, 0, 0), 1)  # vline
                    cv2.line(heatmap, (center[0] + 20, center[1]), (center[0] - 20, center[1]), (0, 0, 0), 1)  # hline
                    
                    # Temperatur anzeigen
                    cv2.putText(heatmap, str(self.img_data['target_temp']) + self.temp_unit, (center[0] + 10, center[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
                    cv2.putText(heatmap, str(self.img_data['target_temp']) + self.temp_unit, (center[0] + 10, center[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

                          
                if self.hud=='all':
                    # display black box for our data
                    cv2.rectangle(heatmap, (0, 0),(160, 120), (0,0,0), -1)
                    # put text in the box
                    cv2.putText(heatmap,'Avg Temp: '+str(self.img_data['avg_temp'])+self.temp_unit, (10, 14),\
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(0, 255, 255), 1, cv2.LINE_AA)
                          
                    cv2.putText(heatmap,'Label Threshold: '+str(self.threshold)+self.temp_unit, (10, 28),\
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
                    if self.img_data['max_temp'] > self.img_data['avg_temp'] + self.threshold:
                        self._draw_circle_text(heatmap, self.img_data['max_temp_y'], self.img_data['max_temp_x'], self.img_data['max_temp'], (0, 0, 255))
                    
                    if self.img_data['min_temp'] < self.img_data['avg_temp'] - self.threshold:
                        self._draw_circle_text(heatmap, self.img_data['min_temp_y'], self.img_data['min_temp_x'], self.img_data['min_temp'], (255, 0, 0))
                
                #display image
                self.heatmap = heatmap
                if self.isqt : cv2.imshow('Thermal', heatmap)
                
                if self.web:
                    self.update_web_frame(heatmap)
                          
                if self.recording == True:
                    try:
                        self.elapsed = (time.time() - self.start)
                    except:
                        self.elapsed = (time.time() - time.time())
                    self.elapsed = time.strftime("%H:%M:%S", time.gmtime(self.elapsed)) 
                    try:
                        self.videoOut.add_frame(heatmap, data = self.img_data)
                    except:
                        self.recording = False
                        
                        
                if self.isqt:
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
                        self.set_target_pos()
                        if self.dispFullscreen == False:
                        	cv2.resizeWindow('Thermal', self.newWidth,self.newHeight)
                            
                    if keyPress == ord('c'): #Decrease scale
                        self.scale -= 1
                        if self.scale <= 1:
                        	self.scale = 1
                        self.newWidth = self.width*self.scale
                        self.newHeight = self.height*self.scale
                        self.set_target_pos()
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
                        self._cycle_hud()
                              
                    if keyPress == ord('m'): #m to cycle through color maps
                        self.colormap = next(self.colormap_options)
                              
                    if keyPress == ord('r'):
                        self._toggle_recording()
                              
                    if keyPress == ord('i'):
                        self.snapshot()
                        
                    if keyPress == ord('o'):
                        self._rotate_image()
                        
                    if keyPress == ord('t'): 
                        self._flip_image()
                        
                    if keyPress == ord('p'):  # oben
                        if self.target_h - self.targetstep >= 0:
                            self.target_h -= self.targetstep
                            self.set_target_pos()
                    if keyPress == 214:  # unten
                        if self.target_h + self.targetstep <= self.height:
                            self.target_h += self.targetstep
                            self.set_target_pos()
                    if keyPress == ord('l'):  # links
                        if self.target_w - self.targetstep >= 0:
                            self.target_w -= self.targetstep
                            self.set_target_pos()
                    if keyPress == 196:  # rechts
                        if self.target_w + self.targetstep <= self.width:
                            self.target_w += self.targetstep
                            self.set_target_pos()
                              
                    if keyPress == ord('q'):
                        self._exit_capture_loop()
                        break
                    
    def _exit_capture_loop(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.__del__()        
        
    def _draw_circle_text(self, heatmap, row, col, temp, color):
        cv2.circle(heatmap, (row, col), 5, (0, 0, 0), 2)
        cv2.circle(heatmap, (row, col), 5, color, -1)
        cv2.putText(heatmap, str(temp) + self.temp_unit, (row + 10, col + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
                
    def _flip_image(self):
        self.flip = next(self.flip_options)


    def _rotate_image(self):
        self.rotation = next(self.rotation_options)
        self.width, self.height = self.height, self.width
        self.newWidth, self.newHeight= self.newHeight, self.newWidth
        self.target_w, self.target_h = self.target_h, self.target_w 
        self.set_target_pos()
        if self.isqt: cv2.destroyAllWindows()
        self.init_windows()
    
    def _cycle_hud(self):
        self.hud = next(self.hud_options)            
    
    def _toggle_recording(self):
        self.recording = next(self.recording_options)

        if self.recording == True:
            self.videoOut = VideoRecorder(self.videostore.camera, self.newWidth, self.newHeight)
            self.start = time.time()
        else:
            self.elapsed = "00:00:00"
            del self.videoOut

                    
    def __del__(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
            
        if self.web == True:
            try:
                self.close_port()
                self.video_thread.join(timeout=0)
                if self.video_thread.is_alive():
                    self.video_thread.terminate()
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
i       : Snapshot photo
m       : Cycle through ColorMaps
h       : Toggle HUD
o       : Rotate image clockwise
t       : Flip image
p/ö/l/ä : Move target position up/down/left/right
"""
        print(info)
        
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Thermal Camera Viewer')
    
    parser.add_argument('--qt', action='store_true', help='Start with QT window')
    parser.add_argument('--port', type=int, default=5001, help='The port for web support (default: 5001)')
    parser.add_argument('--cf', action='store_true', help='Start cloudflared tunnel')
    parser.add_argument('--update', action='store_true', help='Update to the latest version')
    parser.add_argument('--version', action='version', version=f'Thermal Camera Viewer {topdon.__version__}', help='Show the version number of Thermal Camera Viewer')
    parser.add_argument('--camera', type=int, default=-1, help='Specify the camera (default: -1)')

    args = parser.parse_args()
    
    if args.update:
        VersionCheck().ensure_latest_version()
    else:
        self = ThermalCamera(**vars(args))
        self.run()

if __name__ == "__main__":
    self = ThermalCamera(web=True, qt=False)
    self.run()