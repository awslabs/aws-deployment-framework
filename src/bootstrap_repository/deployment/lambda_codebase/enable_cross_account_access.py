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
from kms import KMS


KEY_ID = os.environ['KMS_KEY_ID']
S3_BUCKET = os.environ['S3_BUCKET_NAME']
LOGGER = configure_logger(__name__)


class IAMUpdater():

    target_role_policies = {
        'adf-cloudformation-deployment-role': 'adf-cloudformation-deployment-role-policy',
        'adf-cloudformation-role': 'adf-cloudformation-role-policy'
    }

    role_policies = {
        'adf-codepipeline-role': 'adf-codepipeline-role-policy'
    }

    def __init__(self, kms_key_arn, s3_bucket, role):
        self.iam = IAM(boto3)
        self.iam.update_iam_roles(
            s3_bucket,
            kms_key_arn,
            IAMUpdater.role_policies
        )
        self.iam_target_account = IAM(role)
        self.iam_target_account.update_iam_target_account_roles(
            kms_key_arn,
            IAMUpdater.target_role_policies
        )

def generate_notify_message(event):
    """
    The message we want to pass into the next step (Notify) of the state machine
    if the current account in execution has been bootstrapped
    """
    return {
        "message": "Account {0} has now been bootstrapped into {1}".format(event["account_ids"][0], event["full_path"])
    }

def lambda_handler(event, _):
    sts = STS(boto3)
    parameter_store = ParameterStore(
        event.get('deployment_account_region'),
        boto3
    )
    for region in list(set([event.get('deployment_account_region')] + event.get("regions"))):
        kms_key_arn = parameter_store.fetch_parameter(
            "/cross_region/kms_arn/{0}".format(region)
        )
        s3_bucket = parameter_store.fetch_parameter(
            "/cross_region/s3_regional_bucket/{0}".format(region)
        )
        for account_id in event.get('account_ids'):
            try:
                role = sts.assume_cross_account_role(
                    'arn:aws:iam::{0}:role/{1}'.format(
                        account_id,
                        'adf-cloudformation-deployment-role'
                        ), 'base_cfn_role'
                )
                IAMUpdater(
                    kms_key_arn,
                    s3_bucket,
                    role
                )
                kms = KMS(region, boto3, kms_key_arn, account_id)
                kms.enable_cross_account_access()
            except ClientError:
                continue

    return generate_notify_message(event)
