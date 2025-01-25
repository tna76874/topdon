#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
http stream
"""
import cv2
import numpy as np
import yaml
import os
from itertools import cycle

from flask import Flask, Response
from functools import wraps

try:
    from topdon.video import *
    from topdon.topdon import ThermalFrame
except:
    from video import *
    from topdon import ThermalFrame

class Heatmap:
    def __init__(self, tframe, **kwargs):
        """
        Initialisiert die Heatmap-Klasse mit einer ThermalFrame-Instanz und Konfigurationsoptionen.

        Args:
            tframe (ThermalFrame): Eine Instanz der ThermalFrame-Klasse.
            **kwargs: Zusätzliche Konfigurationswerte.

        Raises:
            TypeError: Falls `tframe` nicht eine Instanz von `ThermalFrame` ist.
        """
        # Validierung des Pflichtarguments
        if not isinstance(tframe, ThermalFrame):
            raise TypeError("tframe muss eine Instanz der ThermalFrame-Klasse sein.")
        self.tframe = tframe

        # Default configurations (übernommen aus dem alten Programm und angepasst)
        self.width = kwargs.get("width", 256)  # Sensor-Breite
        self.height = kwargs.get("height", 192)  # Sensor-Höhe

        self.target_w = kwargs.get("target_w", int(self.width / 2))
        self.target_h = kwargs.get("target_h", int(self.height / 2))

        self.targetstep = kwargs.get("targetstep", 1)
        self.scale = kwargs.get("scale", 3)  # Skalierungsfaktor
        self.new_width = kwargs.get("new_width", self.width * self.scale)
        self.new_height = kwargs.get("new_height", self.height * self.scale)
        self.target = (int(self.new_width * self.target_w / self.width), int(self.new_height* self.target_h / self.height))


        self.alpha = kwargs.get("alpha", 1.0)  # Kontraststeuerung (1.0-3.0)

        # Konfigurationsoptionen für Farbkarten
        self.colormap_options = cycle(kwargs.get("colormap_options", list(range(11))))
        self.colormap = kwargs.get("colormap", next(self.colormap_options))

        self.font = cv2.FONT_HERSHEY_SIMPLEX

        # Rotationsoptionen
        self.rotation_options = cycle(
            kwargs.get(
                "rotation_options",
                [None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE],
            )
        )
        self.rotation = kwargs.get("rotation", next(self.rotation_options))

        # Fullscreen-Anzeigeoptionen
        self.disp_fullscreen_options = cycle(kwargs.get("disp_fullscreen_options", [False, True]))
        self.disp_fullscreen = kwargs.get("disp_fullscreen", next(self.disp_fullscreen_options))

        # Optionen zum Spiegeln des Bildes
        self.flip_options = cycle(kwargs.get("flip_options", [False, True]))
        self.flip = kwargs.get("flip", next(self.flip_options))

        self.rad = kwargs.get("rad", 0)  # Blur-Radius
        self.threshold = kwargs.get("threshold", 2)  # Schwellenwert für Min-/Max-Temperatur
        self.hud_options = cycle(kwargs.get("hud_options", ['spots', 'all', 'cross', 'none']))
        self.hud = kwargs.get("hud", next(self.hud_options))

        self.recording = kwargs.get("recording", False)
        self.elapsed = kwargs.get("elapsed", "00:00:00")
        self.snaptime = kwargs.get("snaptime", "None")

        self.start = None

        self.heatmap = None
        self.thdata = None
        self.temp_unit = kwargs.get("temp_unit", " C")

    def get_frame(self):
        """
        Generiert und gibt die Heatmap basierend auf der aktuellen ThermalFrame-Instanz und den Einstellungen zurück.

        Returns:
            np.ndarray: Die Heatmap als Bild.
        
        Raises:
            ValueError: Falls die ThermalFrame-Instanz ungültig ist.
        """
        if not self.tframe:
            raise ValueError("TFrame wurde nicht gesetzt. Die Instanz ist ungültig.")
        
        # Verarbeite das TFrame
        self.tframe._process_frame()
        self.tframe._set_target(self.target_h, self.target_w)

        img_data = self.tframe._get_data(self.new_width)
        bgr = cv2.cvtColor(self.tframe.imdata, cv2.COLOR_YUV2BGR_YUYV)

        # Kontrast anwenden
        bgr = cv2.convertScaleAbs(bgr, alpha=self.alpha)

        # Resize und Blur anwenden
        bgr = cv2.resize(bgr, (self.new_width, self.new_height), interpolation=cv2.INTER_CUBIC)
        if self.rad > 0:
            bgr = cv2.blur(bgr, (self.rad, self.rad))

        # Farbkarten anwenden
        colormap_dict = {
            0: cv2.COLORMAP_JET, 1: cv2.COLORMAP_HOT, 2: cv2.COLORMAP_MAGMA,
            3: cv2.COLORMAP_INFERNO, 4: cv2.COLORMAP_PLASMA, 5: cv2.COLORMAP_BONE,
            6: cv2.COLORMAP_SPRING, 7: cv2.COLORMAP_AUTUMN, 8: cv2.COLORMAP_VIRIDIS,
            9: cv2.COLORMAP_PARULA, 10: cv2.COLORMAP_RAINBOW
        }
        heatmap = cv2.applyColorMap(bgr, colormap_dict.get(self.colormap, cv2.COLORMAP_JET))
        cmap_text = list(colormap_dict.keys())[self.colormap] if self.colormap in colormap_dict else "Jet"

        if self.colormap == 10:  # Sonderfall für "Inv Rainbow"
            heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

        # Optional HUD hinzufügen
        if self.hud in ['all', 'cross']:
            self._draw_crosshairs(heatmap, img_data)

        if self.hud in ['all' , 'spots']:
            self._draw_hud(heatmap, img_data, cmap_text)

        return heatmap
    
    def _draw_crosshairs(self, heatmap, img_data):
        """
        Zeichnet Fadenkreuze auf die Heatmap.

        Args:
            heatmap (np.ndarray): Das Heatmap-Bild.
            img_data (dict): Die Bilddaten des ThermalFrames.
        """
        center = self.target

        # Weiße Fadenkreuze
        cv2.line(heatmap, (center[0], center[1] + 20), (center[0], center[1] - 20), (255, 255, 255), 2)
        cv2.line(heatmap, (center[0] + 20, center[1]), (center[0] - 20, center[1]), (255, 255, 255), 2)

        # Temperatur anzeigen
        cv2.putText(heatmap, str(img_data['target_temp']) + self.temp_unit, (center[0] + 10, center[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(heatmap, str(img_data['target_temp']) + self.temp_unit, (center[0] + 10, center[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)


    def _draw_hud(self, heatmap, img_data, cmap_text):
        """
        Zeichnet den HUD (Head-Up Display) auf die Heatmap.

        Args:
            heatmap (np.ndarray): Das Heatmap-Bild.
            img_data (dict): Die Bilddaten des ThermalFrames.
            cmap_text (str): Der Name der aktuellen Farbkarte.
        """
        # Schwarzer Hintergrund für den HUD
        cv2.rectangle(heatmap, (0, 0), (160, 25), (0, 0, 0), -1)
        cv2.putText(heatmap, f'avg. temp: {img_data["avg_temp"]}{self.temp_unit}', (10, 14),
                    self.font, 0.4, (0, 255, 255), 1, cv2.LINE_AA)

        if (self.hud!='none'):                      
            if img_data['max_temp'] > img_data['avg_temp'] + self.threshold:
                self._draw_circle_text(heatmap, img_data['max_temp_y'], img_data['max_temp_x'], img_data['max_temp'], (0, 0, 255))
            
            if img_data['min_temp'] < img_data['avg_temp'] - self.threshold:
                self._draw_circle_text(heatmap, img_data['min_temp_y'], img_data['min_temp_x'], img_data['min_temp'], (255, 0, 0))

    def _draw_circle_text(self, heatmap, row, col, temp, color):
        cv2.circle(heatmap, (row, col), 5, (0, 0, 0), 2)
        cv2.circle(heatmap, (row, col), 5, color, -1)
        cv2.putText(heatmap, str(temp) + self.temp_unit, (row + 10, col + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
    
class VideoStreamer:
    def __init__(self,**kwargs):        
        self.videostore = Video()
        self.videostore.open(camera_id=kwargs.get('cam_id', -1))
        self.cap = None

    def _get_cap_size(self):
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)/2)
        return {'width': width, 'height': height}
        
    def _run(self):
        self.cap = self.videostore.cap
  
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            TFrame = ThermalFrame(self.videostore.camera, frame)
            hm = Heatmap(TFrame)
            
            hm_frame = hm.get_frame()

            # Erzeuge den MJPEG-Stream
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + cv2.imencode('.jpg', hm_frame)[1].tobytes() + b'\r\n')



### FLASK APP
app = Flask(__name__)


def error_handling(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return redirect(url_for('video_feed'))
    return wrapper

video_streamer=VideoStreamer()

@app.route('/')
@error_handling
def video_feed():
    return Response(video_streamer._run(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
    

