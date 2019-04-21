# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Stubs for testing parameter_store.py
"""

get_parameter = {
    'Parameter': {
        'Name': 'string',
        'Type': 'String',
        'Value': 'some_parameter_value',
        'Version': 123,
        'Selector': 'string',
        'SourceResult': 'string',
        'LastModifiedDate': 1,
        'ARN': 'string'
    }
}

get_parameters_by_path = {
    'Parameters': [
        {
            'Name': 'string',
            'Type': 'String',
            'Value': 'string',
            'Version': 123,
            'Selector': 'string',
            'SourceResult': 'string',
            'LastModifiedDate': 1,
            'ARN': 'string'
        },
    ],
    'NextToken': 'string'
}
