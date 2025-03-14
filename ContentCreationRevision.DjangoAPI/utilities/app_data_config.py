import json
import os
from django.conf import settings

class AppData:
    def __init__(self) -> None:
        # Get the current directory of the script
        current_dir = os.path.dirname(os.path.realpath(__file__))
        
        # Get the directory of the project root (go up one level)
        project_dir = os.path.dirname(current_dir)
        
        # Construct the full path to the json file
        file_path = os.path.join(project_dir, 'text_config.json')

        with open(file_path) as file:
            self._data = json.load(file)
    
    def get_no_document_text(self)-> str:
        return self._data.get('no_document_text')
    
    def get_file_url(self, input_str: str) -> str:
        # remove file extension to match the key
        keu = input_str.split(".")[0]
        # Replace all spaces with "_", remove all "-", and remove any extra spaces
        key = keu.replace(" ", "_").replace("-", "").strip()
        
        return self._data.get('file_url_mapping')[key]
        
    
    def process_url_title(input_str: str) -> str:
        # Replace all spaces with "_", remove all "-", and remove any extra spaces
        

        return key