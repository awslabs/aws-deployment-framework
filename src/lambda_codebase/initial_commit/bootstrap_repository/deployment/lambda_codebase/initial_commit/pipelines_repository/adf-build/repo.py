# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module used for defining a Pipeline object and the
properties associated with a pipeline.
"""

import os
import boto3
from boto3.session import Session
from cloudformation import CloudFormation
from s3 import S3
from logger import configure_logger

LOGGER = configure_logger(__name__)
TARGET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
DEPLOYMENT_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')
CODE_ACCOUNT_REGION = os.environ.get("AWS_REGION", 'us-east-1')
sts = boto3.client('sts')
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
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

        arn = 'arn:aws:iam::{0}:role/adf-cloudformation-deployment-role'.format(account_id)

        response = sts.assume_role(
            RoleArn=arn,
            RoleSessionName='create_repo_{0}'.format(account_id)
        )
        creds = response['Credentials']
        self.session = Session(
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']
        )

    def repo_exists(self):
        try:
            codecommit = self.session.client('codecommit', CODE_ACCOUNT_REGION)
            repository = codecommit.get_repository(repositoryName=self.name)
            if repository['repositoryMetadata']['Arn']:
                return True
        except BaseException:
            LOGGER.debug("%s - Attempted to find the repo %s but it failed.", self.name)

        return False  # Return False if the Repo Doesnt Exist

    def create_update(self):
        s3_object_path = s3.put_object(
            "repo_templates/codecommit.yml",
            "{0}/repo_templates/codecommit.yml".format(TARGET_DIR)
        )        
        parameters = [{
            'ParameterKey': 'RepoName',
            'ParameterValue': self.name
        }, {
            'ParameterKey': 'Description',
            'ParameterValue': self.description
        }]
        cloudformation = CloudFormation(
            region=CODE_ACCOUNT_REGION,
            deployment_account_region=CODE_ACCOUNT_REGION,
            role=self.session,
            template_url=s3_object_path,
            parameters=parameters,
            wait=True,
            stack_name=self.stack_name,
            s3=None,
            s3_key_path=None,
            account_id=DEPLOYMENT_ACCOUNT_ID,
        )

        # Create the repo stack if the repo is missing and
        create_stack = not self.repo_exists()
        # Update the stack if the repo and the adf contolled stack exist
        update_stack = (self.repo_exists() and cloudformation.get_stack_status())
        if create_stack or update_stack:
            LOGGER.info('Creating Stack for Codecommit Repository %s', self.name)
            cloudformation.create_stack()
