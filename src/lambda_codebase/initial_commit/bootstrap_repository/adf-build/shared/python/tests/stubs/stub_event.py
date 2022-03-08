# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Stubs for testing event.py
"""


class StubEvent():
    def __init__(self):
        self.deployment_account_region = 'us-east-1'
        self.target_regions = ['region-1', 'region-2']
        self.account_id = '123456789012'
        self.deployment_account_id = '111111111111'
