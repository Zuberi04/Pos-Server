import base64
import binascii

from services.pos.entries.process import proc_file



class FileEntries:
    def __init__(self):
        self.suffixes = [".xlxs", ".xls", ".docx", ".pdf", ".csv"]

    def collect_file(self, data: dict):
        if not "file" in data:
            return {"error": "File not passed for processing!"}

        raw= self.clean_file_buffer(data['file'])
        try:    
            file = base64.b64decode(raw)
        except binascii.Error as e:
            print('Exception occured with value: \n', e)
            file = base64.b64decode(raw)
        if not file:
            raise ValueError("Error, string buffer failed to process!!")

        proc = data
        proc['file'] = file
        return proc_file.detect_file_type(proc)

    def add_entry_to_database(self, data: dict):
        if not 'entries' in data:
            return {'error': 'No entries sent to db for processing!!'}
        
        return proc_file.process_entries(data)
    @staticmethod
    def clean_file_buffer( file: str | bytes):
        if not isinstance(file, bytes):
            if file.startswith('data:'):
                raw = file.split(',', 1)[1]
            raw += '=' * (-len(raw) % 4)
            return raw
        return file
                


entries = FileEntries()
