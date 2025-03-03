import json
import sys

def set_path():        
    with open("tests_to_lib.json", "r") as to_lib_file:
        to_lib = json.load(to_lib_file)
        lib_path = to_lib['LIB_PATH']
        with open(lib_path + "insights_config.json", "r") as config_file:
            config = json.load(config_file)
        sys.path.insert(0, lib_path)
        return config