#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
updater modules
"""
import requests
from packaging import version

try:
    import topdon
except:
    pass

class VersionCheck:
    def __init__(self):
        self.repo = 'tna76874/topdon'
        self.title = 'Thermal Cam Viewer'        
        
        self.needs_update = False
        self.checked = False
        self.current_version = None
        self.latest_version = None
        self.run_update_checker()

    
    def run_update_checker(self):
        try:
            self.current_version = topdon.__version__
        except:
            from __init__ import __version__
            self.current_version = __version__

        self.latest_version = self.get_latest_version()
        
        try:
            if self.latest_version!=None:
                self.check_for_update()
                self.checked = True
            else:
                print('Unable to retrieve the latest version.')
        except:
            print('Unable to retrieve the latest version.')


    def get_latest_version(self):
        url = f'https://raw.githubusercontent.com/{self.repo}/master/topdon/__init__.py'
        response = requests.get(url)
        if response.status_code == 200:
            lines = response.text.split('\n')
            for line in lines:
                if line.startswith('__version__'):
                    latest_version = line.split('=')[1].strip().strip("'").strip('"')
                    return latest_version
        return None
    
    def check_for_update(self):
        if version.parse(self.current_version) < version.parse(self.latest_version):
            self.needs_update = True
            print(f'A newer version ({self.latest_version}) is available! Please update your installation.')
        elif version.parse(self.current_version) > version.parse(self.latest_version):
            print(f'The current version ({self.current_version}) is newer than the published version ({self.latest_version})')
        else:
            print(f'Your version ({self.current_version}) is up to date.')
            
    def ensure_latest_version(self):
        if not self.checked:
            self.run_update_checker()
            
        if self.needs_update:    
            try:
                subprocess.run(['pip3', 'install', '--upgrade', f'git+https://github.com/{self.repo}.git'])
                print(f'Successfully updated to: {self.current_version} --> {self.latest_version}')
                exit()
            except Exception as e:
                print(f'Error during update: {e}')
                
if __name__ == "__main__":

    self = VersionCheck()