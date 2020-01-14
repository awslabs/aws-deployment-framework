# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for defining a Pipeline object and the
properties associated with a pipeline.
"""

import os
from cloudformation import CloudFormation
from s3 import S3
from sts import STS
from logger import configure_logger

LOGGER = configure_logger(__name__)
TARGET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
SOURCE_ACCOUNT_REGION = os.environ["AWS_REGION"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
sts = STS()
s3 = S3(
    DEPLOYMENT_ACCOUNT_REGION,
    S3_BUCKET_NAME
)

class Rule:
    def __init__(self, source_account_id):
        self.source_account_id = source_account_id
        self.stack_name = 'adf-event-rule-{0}-{1}'.format(source_account_id, DEPLOYMENT_ACCOUNT_ID)
        # Requirement adf-automation-role to exist on target
        self.role = sts.assume_cross_account_role(
            'arn:aws:iam::{0}:role/adf-automation-role'.format(source_account_id),
            'create_rule_{0}'.format(source_account_id)
        )

    def create_update(self):
        s3_object_path = s3.put_object(
            "adf-build/templates/events.yml",
            "{0}/templates/events.yml".format(TARGET_DIR)
        )
        cloudformation = CloudFormation(
            region=SOURCE_ACCOUNT_REGION,
            deployment_account_region=SOURCE_ACCOUNT_REGION,
            role=self.role,
            template_url=s3_object_path,
            parameters=[],
            wait=True,
            stack_name=self.stack_name,
            s3=None,
            s3_key_path=None,
            account_id=DEPLOYMENT_ACCOUNT_ID,
        )
        LOGGER.info('Ensuring Stack State for Event Rule forwarding from %s to %s', self.source_account_id, DEPLOYMENT_ACCOUNT_ID)
        cloudformation.create_stack()
