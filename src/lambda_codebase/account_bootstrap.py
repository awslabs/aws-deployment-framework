# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Initial step for the Bootstrap process State Machine.
This determines the event and the details about the account
that has been moved and starts the creation of the base CloudFormation
Stack on the target account.
"""

import os
import boto3

from botocore.exceptions import ClientError
from logger import configure_logger
from errors import GenericAccountConfigureError, ParameterNotFoundError
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
    try:
        deployment_account_role = sts.assume_cross_account_role(
            'arn:aws:iam::{0}:role/{1}'.format(
                event['deployment_account_id'],
                event['cross_account_access_role']
            ), 'configure_generic'
        )
        parameter_store_deployment_account = ParameterStore(
            event['deployment_account_region'],
            deployment_account_role
        )
        parameter_store_target_account = ParameterStore(
            region,
            role
        )
        kms_arn = parameter_store_deployment_account.fetch_parameter('/cross_region/kms_arn/{0}'.format(region))
        bucket_name = parameter_store_deployment_account.fetch_parameter('/cross_region/s3_regional_bucket/{0}'.format(region))
    except (ClientError, ParameterNotFoundError):
        raise GenericAccountConfigureError(
            'Account {0} cannot yet be bootstrapped '
            'as the Deployment Account has not yet been bootstrapped. '
            'Have you moved your Deployment account into the deployment OU?'.format(event['account_id'])
        ) from None
    parameter_store_target_account.put_parameter('kms_arn', kms_arn)
    parameter_store_target_account.put_parameter('bucket_name', bucket_name)
    parameter_store_target_account.put_parameter('deployment_account_id', event['deployment_account_id'])

def configure_master_account_parameters(event):
    """
    Update the Master account parameter store in us-east-1 with the deployment_account_id
    then updates the main deployment region with that same value
    """
    parameter_store_master_account_region = ParameterStore(os.environ["AWS_REGION"], boto3)
    parameter_store_master_account_region.put_parameter('deployment_account_id', event['account_id'])
    parameter_store_deployment_account_region = ParameterStore(event['deployment_account_region'], boto3)
    parameter_store_deployment_account_region.put_parameter('deployment_account_id', event['account_id'])

def configure_deployment_account_parameters(event, role):
    """
    Applies the Parameters from adfconfig plus other essential
    Parameters to the Deployment Account in each region as defined in
    adfconfig.yml
    """
    for region in list(set([event["deployment_account_region"]] + event["regions"])):
        parameter_store = ParameterStore(region, role)
        for key, value in event['deployment_account_parameters'].items():
            parameter_store.put_parameter(
                key,
                value
            )

def is_inter_ou_account_move(event):
    return not event["source_ou_id"].startswith('r-') and not event["destination_ou_id"].startswith('r-')

def lambda_handler(event, _):
    sts = STS()
    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            event["account_id"],
            event["cross_account_access_role"]
        ), 'master_lambda'
    )

    if event['is_deployment_account']:
        configure_master_account_parameters(event)
        configure_deployment_account_parameters(event, role)

    s3 = S3(
        region=REGION_DEFAULT,
        bucket=S3_BUCKET
    )

    for region in list(set([event["deployment_account_region"]] + event["regions"])):
        if not event["is_deployment_account"]:
            configure_generic_account(sts, event, region, role)
        cloudformation = CloudFormation(
            region=region,
            deployment_account_region=event["deployment_account_region"],
            role=role,
            wait=True,
            stack_name=None, # Stack name will be automatically defined based on event
            s3=s3,
            s3_key_path=event["full_path"],
            account_id=event["account_id"]
        )
        if is_inter_ou_account_move(event):
            cloudformation.delete_all_base_stacks(True) #override Wait
        cloudformation.create_stack()
        if region == event["deployment_account_region"]:
            cloudformation.create_iam_stack()

    return event
