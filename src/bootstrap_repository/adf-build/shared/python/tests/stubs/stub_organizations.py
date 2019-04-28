# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Stubs for testing organization.py
"""

describe_organization = {
    'Organization': {
        'Id': 'some_org_id',
        'Arn': 'string',
        'FeatureSet': 'ALL',
        'MasterAccountArn': 'string',
        'MasterAccountId': 'some_master_account_id',
        'MasterAccountEmail': 'string',
        'AvailablePolicyTypes': [
            {
                'Type': 'SERVICE_CONTROL_POLICY',
                'Status': 'ENABLED'
            },
        ]
    }
}

list_parents = {
    'Parents': [
        {
            'Id': 'some_id',
            'Type': 'ORGANIZATIONAL_UNIT'
        },
    ],
    'NextToken': 'string'
}

list_parents_root = {
    'Parents': [
        {
            'Id': 'some_id',
            'Type': 'ROOT'
        },
    ],
    'NextToken': 'string'
}

describe_organizational_unit = {
    'OrganizationalUnit': {
        'Id': 'some_org_unit_id',
        'Arn': 'string',
        'Name': 'some_ou_name'
    }
}
