# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module to parse and validate the yaml configuration files.
"""


import os
import yaml
from logger import configure_logger
from .account import Account


LOGGER = configure_logger(__name__)


def read_config_files(folder):
    files = [os.path.join(folder, f) for f in os.listdir(folder)]
    accounts = []
    for filename in files:
        if not filename.endswith(".yml"):
            # Skipping files that do not end with .yml
            continue
        accounts.extend(_read_config_file(filename))

    return accounts


def _read_config_file(filename):
    accounts = []
    try:
        with open(filename, mode='r', encoding='utf-8') as stream:
            config = yaml.safe_load(stream)
            for account in config.get('accounts', []):
                accounts.append(Account.load_from_config(account))
        return accounts
    except Exception as error:
        LOGGER.error(
            "Could not process %s due to an error: %s",
            filename,
            error,
        )
        LOGGER.error(
            "Make sure the content of YAML files (.yml) are not empty and "
            "contain a valid YAML data structure.",
        )
        raise
