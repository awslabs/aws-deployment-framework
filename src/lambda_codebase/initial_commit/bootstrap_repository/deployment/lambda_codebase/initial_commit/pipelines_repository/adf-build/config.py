import os
import yaml

class Config:
    def __init__(self, config_path=None):
        self.config_path = config_path or 'config.yml'
        with open(self.config_path, 'r') as stream:
            self.config=yaml.load(stream, Loader=yaml.FullLoader)
            
    def get_config(self, key, default=None):
        return self.config.get(key, default)
            