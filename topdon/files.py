#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file manager
"""
import os

class FileTypeGeneric:
    def __init__(self, name: str, ending: str, filename: str, path: str):
        self.name = name
        self.ending = ending
        self.filename = filename
        self.path = path

    def delete(self):
        """Löscht die Datei, die mit diesem FileTypeGeneric-Objekt verknüpft ist."""
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
        return f"FileTypeGeneric({self.data()})"
    
class VideoFile(FileTypeGeneric):
    def __init__(self, name: str, filename: str, path: str):
        super().__init__(name, 'mp4', filename, path)

class ImageFile(FileTypeGeneric):
    def __init__(self, name: str, filename: str, path: str):
        super().__init__(name, 'png', filename, path)

class DataFile(FileTypeGeneric):
    def __init__(self, name: str, filename: str, path: str):
        super().__init__(name, 'xlsx', filename, path)
        
class FileBundle:
    def __init__(self, record: FileTypeGeneric, data: DataFile):
        if not self.is_valid_bundle(record, data):
            raise ValueError("Invalid file bundle: names must match and record must be either VideoFile or ImageFile.")
        
        self.record = record
        self.data = data
        self.name = record.name

    def delete(self):
        """Löscht die Dateien im Bundle (record und data)."""
        return self.record.delete() and self.data.delete()

    def get_data(self):
        """Gibt die Informationen des Bundles als Dictionary zurück."""
        return {
            'record': self.record.data(),
            'data': self.data.data(),
            'name': self.name,
        }

    def get_file_list(self):
        """Gibt die Dateiobjekte als Liste zurück."""
        return [self.record, self.data]

    def __repr__(self):
        return f"FileBundleGeneric({self.get_data()})"

    @staticmethod
    def is_valid_bundle(record: FileTypeGeneric, data: DataFile) -> bool:
        """Überprüft, ob das Bundle gültig ist (entweder Video oder Image und Data)."""
        return (
            (isinstance(record, VideoFile) or isinstance(record, ImageFile)) and
            record.name == data.name
        )

class FileManager:
    def __init__(self, base_path: str, slug: str, file_types=None):
        self.base_path = base_path
        self.slug = slug
        self.file_types = file_types if file_types is not None else ['xlsx', 'mp4', 'png']
        
        # Sicherstellen, dass der Basis-Pfad existiert
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def _get_files_list(self):
        """Gibt eine Liste von FileTypeGeneric-Objekten zurück, die Informationen zu den Dateien enthalten."""
        files_info = []
        for file in os.listdir(self.base_path):
            if file.startswith(self.slug) and any(file.endswith(ext) for ext in self.file_types):
                name, ext = os.path.splitext(file)
                ext = ext[1:]  # Entferne den Punkt von der Endung
                path = os.path.join(self.base_path, file)

                # Erstelle das entsprechende FileTypeGeneric-Objekt basierend auf der Endung
                if ext == 'mp4':
                    file_info = VideoFile(name=name, filename=file, path=path)
                elif ext == 'png':
                    file_info = ImageFile(name=name, filename=file, path=path)
                elif ext == 'xlsx':
                    file_info = DataFile(name=name, filename=file, path=path)
                else:
                    continue  # Unbekannter Dateityp, überspringen

                files_info.append(file_info)
        files_info.sort(key=lambda x: x.filename)
        return files_info

    def get_files(self):
        """Erstellt Bundles aus Dateien mit demselben Namen."""
        files_info = self._get_files_list()
        bundles = []
        
        # Erstelle ein Dictionary für DataFiles, um den Zugriff zu erleichtern
        data_files = {file.name: file for file in files_info if isinstance(file, DataFile)}

        # Iteriere über die Dateien und erstelle Bundles
        for file in files_info:
            if isinstance(file, VideoFile) or isinstance(file, ImageFile):
                # Überprüfe, ob ein passendes DataFile existiert
                if file.name in data_files:
                    data_file = data_files[file.name]
                    bundle = FileBundle(record=file, data=data_file)
                    bundles.append(bundle)

        return bundles

    def get_files_list(self):
        """Gibt eine Liste aller DataFile-Objekte aus allen Bundles zurück."""
        bundles = self.get_files()
        data_files_list = []
        
        for bundle in bundles:
            data_files_list.extend(bundle.get_file_list())
            
        data_files_list.sort(key=lambda x: x.filename, reverse=True)
        return data_files_list

    def get_file(self, filename: str):
        """Gibt das FileInfo-Objekt der entsprechenden Datei zurück, oder None, falls es nicht existiert."""
        files_info = self.get_files_list()
        for file_info in files_info:
            if file_info.filename == filename:
                return file_info
        return None

    def get_bundle(self, filename: str):
        """Gibt das passende Bundle für die angegebene Datei zurück, oder None, falls es nicht existiert."""
        name, ext = os.path.splitext(filename)
        bundles = self.get_files()
        
        for bundle in bundles:
            if bundle.name == name:
                return bundle
        
        return None
    

if __name__ == "__main__":
    self = FileManager(base_path=os.getcwd(), slug='TC001')