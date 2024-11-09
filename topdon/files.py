#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file manager
"""
import os

class FileInfo:
    def __init__(self, name: str, ending: str, filename: str, path: str):
        self.name = name
        self.ending = ending
        self.filename = filename
        self.path = path

    def delete(self):
        """Löscht die Datei, die mit diesem FileInfo-Objekt verknüpft ist."""
        if os.path.exists(self.path):
            os.remove(self.path)
            return True
        else:
            return False

    def data(self):
        """Gibt die Dateiinformationen als Dictionary zurück."""
        return {
            'name': self.name,
            'ending': self.ending,
            'filename': self.filename,
            'path': self.path,
        }

    def web_data(self):
        """Gibt die Dateiinformationen als Dictionary zurück."""
        return {
            'name': self.name,
            'ending': self.ending,
            'filename': self.filename,
        }

    def __repr__(self):
        return f"FileInfo({self.data()})"

class FileManager:
    def __init__(self, base_path: str, slug: str, file_types=None):
        self.base_path = base_path
        self.slug = slug
        self.file_types = file_types if file_types is not None else ['xlsx', 'mp4', 'png']
        
        # Sicherstellen, dass der Basis-Pfad existiert
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def get_files(self):
        """Gibt eine Liste von FileInfo-Objekten zurück, die Informationen zu den Dateien enthalten."""
        files_info = []
        for file in os.listdir(self.base_path):
            if file.startswith(self.slug) and any(file.endswith(ext) for ext in self.file_types):
                name, ext = os.path.splitext(file)
                file_info = FileInfo(
                    name=name,
                    ending=ext[1:],  # Entferne den Punkt von der Endung
                    filename=file,
                    path=os.path.join(self.base_path, file)
                )
                files_info.append(file_info)
        files_info.sort(key=lambda x: x.filename)
        return files_info

    def get_file(self, filename: str):
        """Gibt das FileInfo-Objekt der entsprechenden Datei zurück, oder None, falls es nicht existiert."""
        files_info = self.get_files()
        for file_info in files_info:
            if file_info.filename == filename:
                return file_info
        return None
    

if __name__ == "__main__":
    self = FileManager(base_path=os.getcwd(), slug='TC001')