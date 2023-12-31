#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Topdon Viewer

from https://github.com/LeoDJ/P2Pro-Viewer/blob/23887289d3841fdae25c3a11b8d3eed8cd778800/P2Pro/video.py
"""
import platform
import time
import queue
import logging
from typing import Union

import cv2
import numpy as np

if platform.system() == 'Linux':
    import pyudev

topdon_resolution = (256, 384)
topdon_fps = 25.0
topdon_usb_id = (3034, 22576)  # VID, PID

log = logging.getLogger(__name__)

class Video:
    # queue 0 is for GUI, 1 is for recorder
    frame_queue = [queue.Queue(1) for _ in range(2)]
    video_running = False

    @staticmethod
    def list_cap_ids():
        """
        Test the ports and returns a tuple with the available ports and the ones that are working.
        """
        non_working_ids = []
        dev_port = 0
        working_ids = []
        available_ids = []
        log.info("Probing video capture ports...")
        while len(non_working_ids) < 10:
            camera = cv2.VideoCapture(dev_port)
            log.info(f"Testing video capture port {dev_port}... ")
            if not camera.isOpened():
                log.info("Not working.")
                non_working_ids.append(dev_port)
            else:
                is_reading, img = camera.read()
                w = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = camera.get(cv2.CAP_PROP_FPS)
                backend = camera.getBackendName()
                log.info(f"Is present {'and working    ' if is_reading else 'but not working'} [{w}x{h} @ {fps:.1f} FPS ({backend})]")
                if is_reading:
                    # print("Port %s is working and reads images (%s x %s)" %(dev_port,w,h))
                    working_ids.append((dev_port, (w, h), fps, backend))
                else:
                    # print("Port %s for camera ( %s x %s) is present but does not reads." %(dev_port,w,h))
                    available_ids.append(dev_port)

            dev_port += 1
        return working_ids, available_ids, non_working_ids

    # Sadly, Windows APIs / OpenCV is very limited, and the only way to detect the camera is by its characteristic resolution and framerate
    # On Linux, just use the VID/PID via udev
    def get_topdon_cap_id(self):
        if platform.system() == 'Linux':
            for device in pyudev.Context().list_devices(subsystem='video4linux'):
                try:
                    if (int(device.get('ID_VENDOR_ID'), 16), int(device.get('ID_MODEL_ID'), 16)) == topdon_usb_id and \
                            'capture' in device.get('ID_V4L_CAPABILITIES'):
                        return device.get('DEVNAME')
                except:
                    pass
            return None

        # Fallback that uses the resolution and framerate to identify the device
        working_ids, _, _ = self.list_cap_ids()
        for id in working_ids:
            if id[1] == topdon_resolution and id[2] == topdon_fps:
                return id[0]
        return None

    def open(self, camera_id: Union[int, str] = -1):
        if camera_id == -1:
            log.info("No camera ID specified, scanning... (This could take a few seconds)")
            camera_id = self.get_topdon_cap_id()
            if camera_id == None:
                raise ConnectionError(f"Could not find camera module")

        # check if video capture can be opened
        cap = cv2.VideoCapture(camera_id)
        
        if (not cap.isOpened()):
            cap.release()
            #raise ConnectionError(f"Could not open video capture device with index {camera_id}, is the module connected?")

        # check if resolution and FPS matches that of the P2 Pro module
        cap_res = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        cap_fps = cap.get(cv2.CAP_PROP_FPS)
        if (cap_res != topdon_resolution or cap_fps != topdon_fps):
            raise IndexError(
                f"Resolution/FPS of camera id {camera_id} doesn't match. It's probably not a P2 Pro. (Got: {cap_res[0]}x{cap_res[1]}@{cap_fps})")

        # disable automatic YUY2->RGB conversion of OpenCV
        cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        
        self.cap = cap

        # frame_counter = 0

        # while True:
        #     success, frame = cap.read()

        #     if (not success):
        #         continue

        #     self.video_running = True
            
        #     # On Windows, with RGB conversion turned off, OpenCV returns the image as a 2D array with size [1][<imageLen>]. Turn into 1D array. 
        #     if platform.system() == 'Windows':
        #         frame = frame[0]

        #     # split video frame (top is pseudo color, bottom is temperature data)
        #     frame_mid_pos = int(len(frame) / 2)
        #     picture_data = frame[0:frame_mid_pos]
        #     thermal_data = frame[frame_mid_pos:]

        #     # convert buffers to numpy arrays
        #     yuv_picture = np.frombuffer(picture_data, dtype=np.uint8).reshape((topdon_resolution[1] // 2, topdon_resolution[0], 2))
        #     rgb_picture = cv2.cvtColor(yuv_picture, cv2.COLOR_YUV2RGB_YUY2)
        #     thermal_picture_16 = np.frombuffer(thermal_data, dtype=np.uint16).reshape((topdon_resolution[1] // 2, topdon_resolution[0]))

        #     # pack parsed frame data into object
        #     frame_obj = {
        #         "frame_num": frame_counter,
        #         "rgb_data": rgb_picture,
        #         "yuv_data": yuv_picture,
        #         "thermal_data": thermal_picture_16
        #     }

        #     # populate all queues with new frame
        #     for queue in self.frame_queue:
        #         # if queue is full, discard oldest frame (e.g. if frames not read fast enough or at all)
        #         if queue.full():
        #             queue.get(False)
        #         queue.put(frame_obj)

        #     frame_counter += 1


if __name__ == "__main__":
    # test stuff

    # start = time.time()
    # print("P2 Pro capture ID:", get_topdon_cap_id())
    # print(time.time() - start)
    # logging.basicConfig()
    # log.setLevel(logging.INFO)
    # Video().open()

    # context = pyudev.Context()

    
    # devices = [device for device in context.list_devices(subsystem='video4linux')]

    # for device in devices:
    #     print(f"Device: {device}")
    #     for key, value in device.items():
    #         print(f"  {key}: {value}")
    #     print("\n")
        
    pass
