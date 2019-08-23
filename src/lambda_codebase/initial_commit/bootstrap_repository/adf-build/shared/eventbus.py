# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for defining a Pipeline object and the
properties associated with a pipeline.
"""

import os
import boto3
from cloudformation_legacy import CloudFormationLegacy
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


class EventBusPolicy:
    def __init__(self, policy_name, organization_id):
        self.organization_id = organization_id
        self.policy_name = policy_name
        self.stack_name = 'adf-cross-organization-event-policy'
        self.session = boto3

    def define_parameters(self):
        return [{
            'ParameterKey': 'OrganizationId',
            'ParameterValue': self.organization_id
        }, {
            'ParameterKey': 'PolicyName',
            'ParameterValue': self.policy_name
        }]

    def create_update(self):
        s3_object_path = s3.put_object(
            "adf-build/templates/eventbus.yml",
            "{0}/adf-build/templates/eventbus.yml".format(TARGET_DIR)
        )
        cloudformation = CloudFormationLegacy(
            region=CODE_ACCOUNT_REGION,
            deployment_account_region=CODE_ACCOUNT_REGION,
            role=self.session,
            template_url=s3_object_path,
            parameters=self.define_parameters(),
            wait=True,
            stack_name=self.stack_name,
            s3=None,
            s3_key_path=None,
            account_id=DEPLOYMENT_ACCOUNT_ID,
        )

        LOGGER.info('Creating Stack for EventBusPolicy')
        cloudformation.create_stack()
