# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Stubs for testing stepfunction.py
"""

start_execution = {
    'executionArn': 'some_execution_arn',
    'startDate': 123
}

describe_execution = {
    'executionArn': 'string',
    'stateMachineArn': 'string',
    'name': 'string',
    'status': 'RUNNING',
    'startDate': 123,
    'stopDate': 123,
    'input': 'string',
    'output': 'string'
}
