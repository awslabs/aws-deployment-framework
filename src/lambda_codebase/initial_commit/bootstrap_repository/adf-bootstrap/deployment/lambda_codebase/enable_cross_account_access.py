# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


"""
Enables the connection between the deployment account
and the account that is being bootstrapped.
This runs as part of Step Functions on the Deployment Account
"""

import os
import boto3


from botocore.exceptions import ClientError
from logger import configure_logger
from parameter_store import ParameterStore
from sts import STS
from iam import IAM


KEY_ID = os.environ['KMS_KEY_ID']
S3_BUCKET = os.environ['S3_BUCKET_NAME']
LOGGER = configure_logger(__name__)

def update_iam(role, s3_bucket, kms_key_arn, role_policies):
    iam = IAM(role)
    iam.update_iam_roles(
        s3_bucket,
        kms_key_arn,
        role_policies
    )

def lambda_handler(event, _):
    target_role_policies = {
        'adf-cloudformation-deployment-role': 'adf-cloudformation-deployment-role-policy',
        'adf-cloudformation-role': 'adf-cloudformation-role-policy'
    }

    role_policies = {
        'adf-codepipeline-role': 'adf-codepipeline-role-policy',
        'adf-cloudformation-deployment-role': 'adf-cloudformation-deployment-role-policy',
        'adf-cloudformation-role': 'adf-cloudformation-role-policy'
    }

    sts = STS()
    parameter_store = ParameterStore(
        region=event.get('deployment_account_region'),
        role=boto3
    )
    for region in list(set([event.get('deployment_account_region')] + event.get("regions", []))):
        kms_key_arn = parameter_store.fetch_parameter(
            "/cross_region/kms_arn/{0}".format(region)
        )
        s3_bucket = parameter_store.fetch_parameter(
            "/cross_region/s3_regional_bucket/{0}".format(region)
        )
        update_iam(boto3, s3_bucket, kms_key_arn, role_policies)
        for account_id in event.get('account_ids'):
            try:
                role = sts.assume_cross_account_role(
                    'arn:aws:iam::{0}:role/{1}'.format(
                        account_id,
                        'adf-cloudformation-deployment-role'
                        ), 'base_cfn_role'
                )
                LOGGER.debug("Role has bee assumed for %s", account_id)
                update_iam(role, s3_bucket, kms_key_arn, target_role_policies)
            except ClientError:
                LOGGER.debug("%s not yet configured, continuing", account_id)
                continue

    return event
