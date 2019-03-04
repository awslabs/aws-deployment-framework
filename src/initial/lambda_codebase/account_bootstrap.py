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
from cache import Cache
from event import Event
from cloudformation import CloudFormation
from organizations import Organizations
from s3 import S3
from sts import STS

# Globals taken from the lambda environment variables
S3_BUCKET = os.environ["S3_BUCKET_NAME"]
REGION_DEFAULT = os.environ["AWS_REGION"]
LOGGER = configure_logger(__name__)


def configure_generic_account(sts, parsed_event, region, role):
    """
    Fetches the kms_arn from the deployment account main region
    and adds the it plus the deployment_account_id parameter to the
    target account so it can be consumed in CloudFormation. These
    are required for the global.yml in all target accounts.
    """
    deployment_role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            parsed_event.deployment_account_id,
            parsed_event.cross_account_access_role
        ), 'configure_generic'
    )

    kms_arn = ParameterStore(
        parsed_event.deployment_account_region,
        deployment_role
    ).fetch_parameter('/cross_region/kms_arn/{0}'.format(region))
    parameters = ParameterStore(region, role)
    parameters.put_parameter('kms_arn', kms_arn)
    parameters.put_parameter(
        'deployment_account_id',
        parsed_event.deployment_account_id)

def update_master_account_parameters(parsed_event, parameter_store):
    """
    Update the Master account parameter store in us-east-1 with the deployment_account_id
    then updates the main deployment region with that same value
    """
    parameter_store.put_parameter('deployment_account_id', parsed_event.account_id)
    parameter_store = ParameterStore(parsed_event.deployment_account_region, boto3)
    parameter_store.put_parameter('deployment_account_id', parsed_event.account_id)

def configure_deployment_account(parsed_event, role):
    """
    Applies the Parameters from adfconfig plus other essential
    Parameters to the Deployment Account in each region as defined in
    adfconfig.yml
    """
    for region in list(set([parsed_event.deployment_account_region] + parsed_event.regions)):
        parameters = ParameterStore(region, role)
        if region == parsed_event.deployment_account_region:
            for key, value in parsed_event.create_deployment_account_parameters().items():
                if value:
                    parameters.put_parameter(
                        key,
                        value
                    )

        parameters.put_parameter('organization_id', os.environ["ORGANIZATION_ID"])

def lambda_handler(event, _):
    parameters = ParameterStore(REGION_DEFAULT, boto3)
    account_id = event.get(
        'detail').get(
            'requestParameters').get('accountId')
    organizations = Organizations(boto3, account_id)
    parsed_event = Event(event, parameters, organizations, account_id)
    cache = Cache()

    if parsed_event.moved_to_root or parsed_event.moved_to_protected:
        return parsed_event.create_output_object(cache)

    parsed_event.set_destination_ou_name()

    sts = STS(boto3)
    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            parsed_event.account_id,
            parsed_event.cross_account_access_role
        ), 'master_lambda'
    )

    if parsed_event.is_deployment_account:
        update_master_account_parameters(parsed_event, parameters)
        configure_deployment_account(parsed_event, role)

    s3 = S3(REGION_DEFAULT, boto3, S3_BUCKET)

    account_path = parsed_event.organizations.build_account_path(
        parsed_event.destination_ou_id,
        [],  # Initial empty array to hold OU Path,
        cache,
    )

    for region in list(set([parsed_event.deployment_account_region] + parsed_event.regions)):
        if not parsed_event.is_deployment_account:
            configure_generic_account(sts, parsed_event, region, role)
        cloudformation = CloudFormation(
            region=region,
            deployment_account_region=parsed_event.deployment_account_region,
            role=role,
            wait=False,
            stack_name=None,
            s3=s3,
            s3_key_path=account_path
        )
        cloudformation.create_stack()

    return parsed_event.create_output_object(cache)
