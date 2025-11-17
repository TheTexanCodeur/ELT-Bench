import signal
import os
import hashlib
import shutil
from typing import Dict
import os
import pandas as pd
import json
import xml.etree.ElementTree as ET
import yaml


TIMEOUT_DURATION = 25

def is_file_valid(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.csv':
            pd.read_csv(file_path)
        elif ext == '.json':
            with open(file_path, 'r') as f:
                json.load(f)
        elif ext == '.xml':
            ET.parse(file_path)
        elif ext == '.yaml' or ext == '.yml':
            with open(file_path, 'r') as f:
                yaml.safe_load(f)
        else:
            return True, None
        return True, None
    except Exception as e:
        return False, str(e)
        
class timeout:
    def __init__(self, seconds=TIMEOUT_DURATION, error_message="Timeout"):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


def delete_files_in_folder(folder_path):
    if os.path.exists(folder_path):
        files = os.listdir(folder_path)
        for file in files:
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        
def create_folder_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def calculate_sha256(file_path):
    with open(file_path, 'rb') as f:
        file_data = f.read()
        return hashlib.sha256(file_data).hexdigest()

class PostProcessor:
    def __init__(self, wrk_dir: str):
        self.wrk_dir = wrk_dir
        self.init_files_hash = self._get_env_files_hash()
    
        
    def _get_env_files_hash(self) -> Dict[str, str]:
        """
        Returns:
            Dict[str, str]: a dictionary of the hash of the files in the
              environment
        """
        files_hash = {}
        for root, dirs, files in os.walk(self.wrk_dir):
            for f in files:
                file_path = os.path.join(root, f)
                files_hash[file_path] = calculate_sha256(file_path)
        return files_hash
        
        
    def _find_diff_files_init(self, init_file_dict)-> Dict:
        init_file_paths = init_file_dict.keys()
        added_files_list = []
        changed_files_list = []
        for root, dirs, files in os.walk(self.wrk_dir):
            for f in files:
                file_path = os.path.join(root, f)
                if file_path not in init_file_paths:
                    added_files_list.append(file_path)
                else:
                    if init_file_dict[file_path] != calculate_sha256(file_path):
                        changed_files_list.append(file_path)
        return {"added_files": added_files_list, "changed_files": changed_files_list}
    
    
    def post_process(self):
        """
        Evaluate whether the task is successfully completed.
        """
        diff_files = self._find_diff_files_init(self.init_files_hash)
        
        return {**diff_files}
    