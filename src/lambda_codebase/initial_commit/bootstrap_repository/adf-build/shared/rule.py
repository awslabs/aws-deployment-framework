# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
DEPLOYMENT_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')
CODE_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')
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
        self.session = sts.assume_cross_account_role(
            'arn:aws:iam::{0}:role/adf-cloudformation-deployment-role'.format(source_account_id),
            'create_rule_{0}'.format(source_account_id)
        )

    def define_repo_parameters(self):
        return [{
            'ParameterKey': 'SourceAccountId',
            'ParameterValue': str(self.source_account_id)
        }, {
            'ParameterKey': 'DeployAccountId',
            'ParameterValue': str(DEPLOYMENT_ACCOUNT_ID)
        }]

    def create_update(self):
        s3_object_path = s3.put_object(
            "adf-build/templates/source_account_rules.yml",
            "{0}/adf-build/templates/source_account_rules.yml".format(TARGET_DIR)
        )
        cloudformation = CloudFormation(
            region=CODE_ACCOUNT_REGION,
            deployment_account_region=CODE_ACCOUNT_REGION,
            role=self.session,
            template_url=s3_object_path,
            parameters=self.define_repo_parameters(),
            wait=True,
            stack_name=self.stack_name,
            s3=None,
            s3_key_path=None,
            account_id=DEPLOYMENT_ACCOUNT_ID,
        )

        LOGGER.info('Creating Stack for Event Rule forwarding from %s to %s', self.source_account_id, DEPLOYMENT_ACCOUNT_ID)
        cloudformation.create_stack()
