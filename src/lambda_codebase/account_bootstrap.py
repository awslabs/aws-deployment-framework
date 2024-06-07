# Copyright Amazon.com Inc. or its affiliates.
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

# ADF imports
from errors import (
    AccountCreationNotFinishedError,
    GenericAccountConfigureError,
    ParameterNotFoundError,
)
from cloudformation import CloudFormation
from logger import configure_logger
from parameter_store import ParameterStore
from partition import get_partition
from s3 import S3
from sts import STS

# Globals taken from the lambda environment variables
S3_BUCKET = os.environ["S3_BUCKET_NAME"]
REGION_DEFAULT = os.environ["AWS_REGION"]
PARTITION = get_partition(REGION_DEFAULT)
MANAGEMENT_ACCOUNT_ID = os.environ["MANAGEMENT_ACCOUNT_ID"]
LOGGER = configure_logger(__name__)
DEPLOY_TIME_IN_MS = 5 * 60 * 1000


def configure_generic_account(sts, event, region, role):
    """
    Fetches the kms_arn from the deployment account main region
    and adds the it plus the deployment_account_id parameter to the
    target account so it can be consumed in CloudFormation. These
    are required for the global.yml in all target accounts.
    """
    try:
        deployment_account_id = event['deployment_account_id']
        cross_account_access_role = event['cross_account_access_role']

        deployment_account_role = sts.assume_bootstrap_deployment_role(
            PARTITION,
            MANAGEMENT_ACCOUNT_ID,
            deployment_account_id,
            cross_account_access_role,
            'configure_generic',
        )

        parameter_store_deployment_account = ParameterStore(
            event['deployment_account_region'],
            deployment_account_role,
        )
        parameter_store_target_account = ParameterStore(
            region,
            role,
        )
        kms_arn = parameter_store_deployment_account.fetch_parameter(
            f'cross_region/kms_arn/{region}',
        )
        bucket_name = parameter_store_deployment_account.fetch_parameter(
            f'cross_region/s3_regional_bucket/{region}',
        )
        org_stage = parameter_store_deployment_account.fetch_parameter(
            'org/stage',
        )
    except (ClientError, ParameterNotFoundError):
        raise GenericAccountConfigureError(
            f'Account {event["account_id"]} cannot yet be bootstrapped '
            'as the Deployment Account has not yet been bootstrapped. '
            'Have you moved your Deployment account into the deployment OU?'
        ) from None
    parameter_store_target_account.put_parameter('kms_arn', kms_arn)
    parameter_store_target_account.put_parameter('bucket_name', bucket_name)
    parameter_store_target_account.put_parameter(
        'deployment_account_id',
        event['deployment_account_id'],
    )
    if region == event['deployment_account_region']:
        parameter_store_target_account.put_parameter(
            'management_account_id',
            MANAGEMENT_ACCOUNT_ID,
        )
        parameter_store_target_account.put_parameter(
            'bootstrap_templates_bucket',
            S3_BUCKET,
        )
    parameter_store_target_account.put_parameter('org/stage', org_stage)


def configure_management_account_parameters(event):
    """
    Update the management account parameter store in us-east-1 with the
    deployment_account_id then updates the main deployment region
    with that same value
    """
    parameter_store_management_account_region = ParameterStore(
        os.environ["AWS_REGION"],
        boto3,
    )
    parameter_store_management_account_region.put_parameter(
        'deployment_account_id',
        event['account_id'],
    )
    parameter_store_deployment_account_region = ParameterStore(
        event['deployment_account_region'],
        boto3,
    )
    parameter_store_deployment_account_region.put_parameter(
        'deployment_account_id',
        event['account_id'],
    )


def configure_deployment_account_parameters(event, role):
    """
    Applies the Parameters from adfconfig plus other essential
    Parameters to the Deployment Account in each region as defined
    in adfconfig.yml
    """
    regions = list(
        set(
            [event["deployment_account_region"]]
            + event["regions"]
        )
    )
    for region in regions:
        parameter_store = ParameterStore(region, role)
        for key, value in event['deployment_account_parameters'].items():
            parameter_store.put_parameter(key, value)


def lambda_handler(event, context):
    try:
        return _lambda_handler(event, context)
    except ClientError as error:
        if error.response['Error']['Code'] == 'SubscriptionRequiredException':
            raise AccountCreationNotFinishedError(
                f"The AWS Account is not ready yet. Error thrown: {error}"
            ) from error
        raise


def _lambda_handler(event, context):
    sts = STS()

    account_id = event["account_id"]
    cross_account_access_role = event["cross_account_access_role"]

    role = sts.assume_bootstrap_deployment_role(
        PARTITION,
        MANAGEMENT_ACCOUNT_ID,
        account_id,
        cross_account_access_role,
        'management_lambda',
    )

    if event['is_deployment_account']:
        configure_management_account_parameters(event)
        configure_deployment_account_parameters(event, role)

    s3 = S3(
        region=REGION_DEFAULT,
        bucket=S3_BUCKET,
    )

    regions = list(
        set(
            [event["deployment_account_region"]]
            + event["regions"]
        )
    )
    LOGGER.debug(
        "Looping through regions to deploy the base stack in %s, regions: %s",
        event["account_id"],
        regions,
    )
    for region in regions:
        if context.get_remaining_time_in_millis() < DEPLOY_TIME_IN_MS:
            LOGGER.info(
                "Cannot deploy another region, as the time available for this "
                "lambda execution is less than the time required to deploy."
            )
            raise GenericAccountConfigureError(
                'Execution time remaining is not sufficient to deploy '
                'another region, aborting this execution so it can restart.'
            )
        if not event["is_deployment_account"]:
            configure_generic_account(sts, event, region, role)
        LOGGER.info(
            "Creating/updating base stack in %s %s",
            event["account_id"],
            region,
        )
        cloudformation = CloudFormation(
            region=region,
            deployment_account_region=event["deployment_account_region"],
            role=role,
            wait=True,
            # Stack name will be automatically defined based on event
            stack_name=None,
            s3=s3,
            s3_key_path=event["full_path"],
            account_id=account_id
        )
        cloudformation.create_stack()
        if region == event["deployment_account_region"]:
            cloudformation.create_iam_stack()

    return event
