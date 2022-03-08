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
from partition import get_partition

LOGGER = configure_logger(__name__)
TARGET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
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
        self.stack_name = f"adf-codecommit-{self.name}"
        self.account_id = account_id
        self.partition = get_partition(DEPLOYMENT_ACCOUNT_REGION)
        self.session = sts.assume_cross_account_role(
            f'arn:{self.partition}:iam::{account_id}:role/adf-automation-role',
            f'create_repo_{account_id}'
        )

    def repo_exists(self):
        try:
            codecommit = self.session.client('codecommit', DEPLOYMENT_ACCOUNT_REGION)
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
            "adf-build/templates/codecommit.yml",
            f"{TARGET_DIR}/adf-build/templates/codecommit.yml",
        )
        cloudformation = CloudFormation(
            region=DEPLOYMENT_ACCOUNT_REGION,
            deployment_account_region=DEPLOYMENT_ACCOUNT_REGION,
            role=self.session,
            template_url=s3_object_path,
            parameters=self.define_repo_parameters(),
            wait=True,
            stack_name=self.stack_name,
            s3=None,
            s3_key_path=None,
            account_id=DEPLOYMENT_ACCOUNT_ID,
        )
        # Update the stack if the repo and the ADF controlled stack exist,
        # return if the repo exists but no stack (previously made)
        _repo_exists = self.repo_exists()
        _stack_exists = cloudformation.get_stack_status()
        if _repo_exists and not _stack_exists:
            return
        if not _repo_exists and not _stack_exists:
            LOGGER.info(
                'Ensuring State for CodeCommit Repository Stack %s on Account %s',
                self.name,
                self.account_id,
            )
            cloudformation.create_stack()
