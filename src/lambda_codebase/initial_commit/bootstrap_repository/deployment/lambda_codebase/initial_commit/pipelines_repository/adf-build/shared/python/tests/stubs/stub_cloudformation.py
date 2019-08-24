# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Stubs for testing cloudformation.py
"""

describe_stack = {
    'Stacks': [{
        'Outputs': [{
            'OutputKey': "DeploymentFrameworkRegionalKMSKey",
            'OutputValue': "some_key_arn"
        }, {
            'OutputKey': "DeploymentFrameworkRegionalS3Bucket",
            'OutputValue': "some_bucket_name"
        }],
        'StackStatus': 'CREATE_IN_PROGRESS'
    }]
}
