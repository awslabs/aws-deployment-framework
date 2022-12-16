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
from partition import get_partition
from .iam_cfn_deploy_role_policy import IAMCfnDeployRolePolicy


KEY_ID = os.environ["KMS_KEY_ID"]
S3_BUCKET = os.environ["S3_BUCKET_NAME"]
REGION_DEFAULT = os.getenv("AWS_REGION")
LOGGER = configure_logger(__name__)

# Target Role Policies are updated in target accounts
TARGET_ROLE_POLICIES = {
    'adf-cloudformation-deployment-role': [
        'adf-cloudformation-deployment-role-policy-kms',
    ],
    "adf-cloudformation-role": [
        "adf-cloudformation-role-policy",
        "adf-cloudformation-role-policy-s3",
        "adf-cloudformation-role-policy-kms",
    ],
}

# Role Policies are updated in the deployment account.
DEPLOYMENT_ROLE_POLICIES = {
    "adf-codepipeline-role": [
        "adf-codepipeline-role-policy",
        "adf-codepipeline-role-policy-s3",
        "adf-codepipeline-role-policy-kms",
    ],
    "adf-cloudformation-deployment-role": [
        "adf-cloudformation-deployment-role-policy",
    ],
    "adf-cloudformation-role": [
        "adf-cloudformation-role-policy",
    ],
}


def lambda_handler(event, _):
    """
    Lambda handler of the enable cross-account access orchestrator.
    This process will ensure that the deployment account and target regions
    are able to use the correct ADF S3 buckets and KMS keys.

    Args:
        event (any): The input event submitted to AWS Lambda. This event will
            hold the deployment_account_region, target regions, and account id
            that should be configured.

    Returns:
        event (any): The input event that was submitted is passed forward, so
            the next step in the State Machine is able to use the data too.
    """
    sts = STS()
    partition = get_partition(REGION_DEFAULT)

    parameter_store = ParameterStore(
        region=event.get("deployment_account_region"), role=boto3
    )
    account_id = event.get("account_id")
    try:
        role_arn_to_assume = (
            f'arn:{partition}:iam::{account_id}:'
            f'role/adf-cloudformation-deployment-role'
        )
        target_account_role = sts.assume_cross_account_role(
            role_arn_to_assume,
            'base_cfn_role'
        )
        LOGGER.debug("Role has been assumed for %s", account_id)
    except ClientError as err:
        LOGGER.error(
            "Could not assume into account %s with role %s -> error: %s.",
            role_arn_to_assume,
            account_id,
            err,
            exc_info=True,
        )
        raise

    kms_key_arns = []
    s3_buckets = []
    for region in list(
        set(
            [event.get("deployment_account_region")]
            + event.get("regions", [])
        )
    ):
        kms_key_arn = parameter_store.fetch_parameter(
            f"/cross_region/kms_arn/{region}"
        )
        kms_key_arns.append(kms_key_arn)
        s3_bucket = parameter_store.fetch_parameter(
            f"/cross_region/s3_regional_bucket/{region}"
        )
        s3_buckets.append(s3_bucket)
        IAMCfnDeployRolePolicy.update_iam_role_policies(
            target_account_role.client("iam"),
            [s3_bucket],  # Only the S3 bucket for this region
            [kms_key_arn],  # Only the KMS Key for this region
            TARGET_ROLE_POLICIES,
        )

    IAMCfnDeployRolePolicy.update_iam_role_policies(
        boto3.client("iam"),
        s3_buckets,
        kms_key_arns,
        DEPLOYMENT_ROLE_POLICIES,
    )

    return event
