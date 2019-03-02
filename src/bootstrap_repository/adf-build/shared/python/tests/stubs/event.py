# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Stubs for testing event.py
"""


class StubEvent():
    def __init__(self):
        self.deployment_account_region = 'us-east-1'
        self.target_regions = ['region-1', 'region-2']
        self.account_id = '12345678910'
        self.deployment_account_id = '9999911111'
