# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module to parse and validate the yaml configuration files.
"""


import os
import yaml
from .account import Account


def read_config_files(folder):
    files = [os.path.join(folder, f) for f in os.listdir(folder)]
    accounts = []
    for filename in files:
        if filename.endswith(".yml"):
            with open(filename, 'r') as stream:
                config = yaml.safe_load(stream)
                for account in config.get('accounts', []):
                    accounts.append(Account.load_from_config(account))
    return accounts
