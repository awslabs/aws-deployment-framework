# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Initial step for the Bootstrap process State Machine.
This determines the event and the details about the account
that has been moved and starts the creation of the base CloudFormation
Stack on the target account.
"""

import os
import boto3

from logger import configure_logger
from parameter_store import ParameterStore
from cloudformation import CloudFormation
from s3 import S3
from sts import STS

# Globals taken from the lambda environment variables
S3_BUCKET = os.environ["S3_BUCKET_NAME"]
REGION_DEFAULT = os.environ["AWS_REGION"]
LOGGER = configure_logger(__name__)


def configure_generic_account(sts, event, region, role):
    """
    Fetches the kms_arn from the deployment account main region
    and adds the it plus the deployment_account_id parameter to the
    target account so it can be consumed in CloudFormation. These
    are required for the global.yml in all target accounts.
    """
    deployment_role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            event['deployment_account_id'],
            event['cross_account_iam_role']
        ), 'configure_generic'
    )

    kms_arn = ParameterStore(
        event['deployment_account_region'],
        deployment_role
    ).fetch_parameter('/cross_region/kms_arn/{0}'.format(region))
    parameters = ParameterStore(region, role)
    parameters.put_parameter('kms_arn', kms_arn)
    parameters.put_parameter(
        'deployment_account_id',
        event['deployment_account_id'])

def update_master_account_parameters(event, parameter_store):
    """
    Update the Master account parameter store in us-east-1 with the deployment_account_id
    then updates the main deployment region with that same value
    """
    parameter_store.put_parameter('deployment_account_id', event['account_id'])
    parameter_store = ParameterStore(event['deployment_account_region'], boto3)
    parameter_store.put_parameter('deployment_account_id', event['account_id'])

def configure_deployment_account(event, role):
    """
    Applies the Parameters from adfconfig plus other essential
    Parameters to the Deployment Account in each region as defined in
    adfconfig.yml
    """
    for region in list(set([event['deployment_account_region']] + event['regions'])):
        parameters = ParameterStore(region, role)
        if region == event['deployment_account_region']:
            for key, value in event['deployment_account_parameters'].items():
                if value:
                    parameters.put_parameter(
                        key,
                        value
                    )

def lambda_handler(event, _):
    sts = STS(boto3)
    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            event["account_id"],
            event["cross_account_iam_role"]
        ), 'master_lambda'
    )

    if event['is_deployment_account']:
        update_master_account_parameters(event, ParameterStore(REGION_DEFAULT, boto3))
        configure_deployment_account(event, role)

    s3 = S3(REGION_DEFAULT, boto3, S3_BUCKET)

    for region in list(set([event["deployment_account_region"]] + event["regions"])):
        if not event["is_deployment_account"]:
            configure_generic_account(sts, event, region, role)
        cloudformation = CloudFormation(
            region=region,
            deployment_account_region=event["deployment_account_region"],
            role=role,
            wait=False,
            stack_name=None,
            s3=s3,
            s3_key_path=event["full_path"]
        )
        cloudformation.create_stack()

    return event
