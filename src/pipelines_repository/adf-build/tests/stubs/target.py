# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

"""
Stubs used for testing target.py
"""

stub_target_is_approval = {
    'name': 'approval',
    'id': 'approval',
    'path': '/thing/path',
    'regions': ['region1', 'region2']
}

stub_create_target_info_default = {
    'name': 'account_name',
    'id': 12345678910,
    'path': '/thing/path',
    'regions': ['region1', 'region2']
}

stub_create_target_info_regex_applied = {
    'name': 'accountname',
    'id': 12345678910,
    'path': '/thing/path',
    'regions': ['region1', 'region2']
}

stub_target_output = {
    'name': 'string',
    'id': 'fake',
    'path': '/thing/path',
    'regions': ['region1', 'region2']
}

stub_organizations_describe_account = {
    'Account': {
        'Id': 'fake',
        'Arn': 'fake::arn',
        'Email': 'fake@fake.com',
        'Name': 'string',
        'Status': 'ACTIVE',
        'JoinedMethod': 'INVITED',
        'JoinedTimestamp': 2
    }
}


def stub_organizations_dir_to_ou():
    yield {
        'Id': 'fake',
        'Arn': 'fake::arn',
        'Email': 'fake@fake.com',
        'Name': 'string',
        'Status': 'ACTIVE',
        'JoinedMethod': 'INVITED',
        'JoinedTimestamp': 2
    }


def stub_organizations_list_accounts_for_parent():
    yield {
        'Id': 'fake',
        'Arn': 'fake::arn',
        'Email': 'fake@fake.com',
        'Name': 'string',
        'Status': 'ACTIVE',
        'JoinedMethod': 'CREATED',
        'JoinedTimestamp': 2
    }