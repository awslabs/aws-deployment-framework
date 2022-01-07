# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

"""
Stubs used for testing target.py
"""


target_is_approval = {
    'name': 'approval',
    'id': 'approval',
    'path': '/thing/path',
    "properties": {},
    "provider": 'approval',
    'regions': ['region1', 'region2'],
    'step_name': {}
}

create_target_info_default = {
    'name': 'account_name',
    'id': 123456789012,
    'path': '/thing/path',
    "properties": {},
    "provider": 'cloudformation',
    'regions': ['region1', 'region2'],
    'step_name': {}
}

create_target_info_regex_applied = {
    'name': 'accountname',
    'id': 123456789012,
    'path': '/thing/path',
    "properties": {},
    "provider": 'cloudformation',
    'regions': ['region1', 'region2'],
    'step_name': {}
}

target_output = {
    'name': 'string',
    'id': 'fake',
    'path': '/thing/path',
    "properties": {},
    "provider": 'cloudformation',
    'regions': ['region1', 'region2'],
    'step_name': {}
}

target_tags = {
    'name': 'string',
    'id': 'fake',
    'tags': {'solution': 'connected', 'environment': 'prod'},
    "properties": {},
    "provider": 'cloudformation',
    'regions': ['region1', 'region2'],
    'step_name': {}
}


organizations_describe_account = {
    'Account': {
        'Id': 'fake',
        'Arn': 'fake::arn',
        'Email': 'jane@example.com',
        'Name': 'string',
        'Status': 'ACTIVE',
        'JoinedMethod': 'INVITED',
        'JoinedTimestamp': 2
    }
}


def organizations_dir_to_ou():
    yield {
        'Id': 'fake',
        'Arn': 'fake::arn',
        'Email': 'jane@example.com',
        'Name': 'string',
        'Status': 'ACTIVE',
        'JoinedMethod': 'INVITED',
        'JoinedTimestamp': 2
    }


def organizations_list_accounts_for_parent():
    yield {
        'Id': 'fake',
        'Arn': 'fake::arn',
        'Email': 'jane@example.com',
        'Name': 'string',
        'Status': 'ACTIVE',
        'JoinedMethod': 'CREATED',
        'JoinedTimestamp': 2
    }
