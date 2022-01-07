# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from partition import get_partition


KEY_ID = os.environ['KMS_KEY_ID']
S3_BUCKET = os.environ['S3_BUCKET_NAME']
REGION_DEFAULT = os.getenv('AWS_REGION')
LOGGER = configure_logger(__name__)


def update_iam(role, s3_buckets, kms_key_arns, role_policies):
    iam = IAM(role.client("iam"))
    iam.update_iam_roles(
        s3_buckets,
        kms_key_arns,
        role_policies
    )


def lambda_handler(event, _):
    target_role_policies = {
        'adf-cloudformation-deployment-role': 'adf-cloudformation-deployment-role-policy-kms',
        'adf-cloudformation-role': 'adf-cloudformation-role-policy'
    }

    role_policies = {
        'adf-codepipeline-role': 'adf-codepipeline-role-policy',
        'adf-cloudformation-deployment-role': 'adf-cloudformation-deployment-role-policy',
        'adf-cloudformation-role': 'adf-cloudformation-role-policy'
    }

    sts = STS()
    partition = get_partition(REGION_DEFAULT)

    parameter_store = ParameterStore(
        region=event.get('deployment_account_region'),
        role=boto3
    )
    account_id = event.get("account_id")
    kms_key_arns = []
    s3_buckets = []
    for region in list(set([event.get('deployment_account_region')] + event.get("regions", []))):
        kms_key_arn = parameter_store.fetch_parameter(
            f"/cross_region/kms_arn/{region}"
        )
        kms_key_arns.append(kms_key_arn)
        s3_bucket = parameter_store.fetch_parameter(
            f"/cross_region/s3_regional_bucket/{region}"
        )
        s3_buckets.append(s3_bucket)
        try:
            role = sts.assume_cross_account_role(
                f'arn:{partition}:iam::{account_id}:role/adf-cloudformation-deployment-role',
                'base_cfn_role'
            )
            LOGGER.debug("Role has been assumed for %s", account_id)
            update_iam(role, s3_bucket, kms_key_arn, target_role_policies)
        except ClientError as err:
            LOGGER.debug("%s could not be assumed (%s), continuing", account_id, err, exc_info=True)
            continue

    update_iam(boto3, s3_buckets, kms_key_arns, role_policies)

    return event
