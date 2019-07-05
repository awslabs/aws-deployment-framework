# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for loading Config from the config.yml.
"""

import yaml

class Config:
    def __init__(self, config_path=None):
        self.config_path = config_path or 'config.yml'
        with open(self.config_path, 'r') as stream:
            self.config = yaml.load(stream, Loader=yaml.FullLoader)

    def get_config(self, key, default=None):
        return self.config.get(key, default)
