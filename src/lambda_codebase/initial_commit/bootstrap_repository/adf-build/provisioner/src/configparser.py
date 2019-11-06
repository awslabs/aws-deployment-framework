"""
# configparser.py

Module to parse and validate the yaml configuration files.
"""
import yaml
import os
from .account import Account


def read_config_files(folder):
    """Retrieve account objects from yaml configuration files in given folder.
    :param folder: Folder containing config files
    :return: list of tuples [(full_account_name, email, ou_path), ]
    """
    files = [os.path.join(folder, f) for f in os.listdir(folder)]
    accounts = []
    for filename in files:
        with open(filename, 'r') as stream:
            config = yaml.safe_load(stream)

            for account in config['accounts']:
                accounts.append(Account.load_from_config(account))

    return accounts
