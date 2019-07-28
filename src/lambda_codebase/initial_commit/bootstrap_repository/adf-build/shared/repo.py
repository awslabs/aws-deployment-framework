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
class Repo:
    def __init__(self, account_id, name, description=''):
        self.name = name
        if not description:
            description = 'Created by ADF'

        self.description = description
        self.stack_name = "{0}-{1}".format('adf-codecommit', self.name)
        self.account_id = account_id
        self.session = sts.assume_cross_account_role(
            'arn:aws:iam::{0}:role/adf-cloudformation-deployment-role'.format(account_id),
            'create_repo_{0}'.format(account_id)
        )

    def repo_exists(self):
        try:
            codecommit = self.session.client('codecommit', CODE_ACCOUNT_REGION)
            repository = codecommit.get_repository(repositoryName=self.name)
            if repository['repositoryMetadata']['Arn']:
                return True
        except Exception: # pylint: disable=broad-except
            LOGGER.debug('Attempted to find the repo %s but it failed.', self.name)
        return False  # Return False if the Repo Doesnt Exist

    def define_repo_parameters(self):
        return [{
            'ParameterKey': 'RepoName',
            'ParameterValue': self.name
        }, {
            'ParameterKey': 'Description',
            'ParameterValue': self.description
        }]

    def create_update(self):
        s3_object_path = s3.put_object(
            "adf-build/repo_templates/codecommit.yml",
            "{0}/adf-build/repo_templates/codecommit.yml".format(TARGET_DIR)
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

        # Update the stack if the repo and the adf contolled stack exist
        update_stack = (self.repo_exists() and cloudformation.get_stack_status())
        if not self.repo_exists() or update_stack:
            LOGGER.info('Creating Stack for Codecommit Repository %s on Account %s', self.name, self.account_id)
            cloudformation.create_stack()
