# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Executes as part of Step Functions when an AWS Account
is moved to the root of the Organization.
"""

import ast
import os
from thread import PropagatingThread

import boto3

# ADF imports
from cloudformation import CloudFormation
from logger import configure_logger
from parameter_store import ParameterStore
from partition import get_partition
from sts import STS

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.environ.get('AWS_REGION')
MANAGEMENT_ACCOUNT_ID = os.getenv('MANAGEMENT_ACCOUNT_ID')
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")

ADF_PARAM_DESCRIPTION = 'Used by The AWS Deployment Framework'


def worker_thread(region, account_id, role, event):
    parameter_store = ParameterStore(region, role)
    paginator = parameter_store.client.get_paginator('describe_parameters')
    page_iterator = paginator.paginate()
    for page in page_iterator:
        for parameter in page['Parameters']:
            description = parameter.get('Description', '')
            if ADF_PARAM_DESCRIPTION in description:
                parameter_store.delete_parameter(parameter.get('Name'))

    cloudformation = CloudFormation(
        region=region,
        deployment_account_region=event.get('deployment_account_region'),
        role=role,
        wait=True,
        stack_name=None,
        s3=None,
        s3_key_path=None,
        account_id=account_id
    )
    return cloudformation.delete_all_base_stacks()


def remove_base(account_id, regions, privileged_role_name, event):
    sts = STS()
    threads = []

    partition = get_partition(REGION_DEFAULT)

    role = sts.assume_bootstrap_deployment_role(
        partition,
        MANAGEMENT_ACCOUNT_ID,
        account_id,
        privileged_role_name,
        'remove_base',
    )

    regions = list(
        # Set to ensure we only have one of each
        set(
            # Make sure the deployment_account_region is in the list of
            # regions:
            [event.get('deployment_account_region')]
            + regions
        )
    )
    for region in regions:
        thread = PropagatingThread(
            target=worker_thread,
            args=(
                region,
                account_id,
                role,
                event,
            ),
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


def execute_move_action(action, account_id, parameter_store, event):
    LOGGER.info('Move to root action is %s for account %s', action, account_id)
    if action in ['remove_base', 'remove-base']:
        regions = (
            ast.literal_eval(
                parameter_store.fetch_parameter('target_regions')
            )
            or []
        )

        privileged_role_name = parameter_store.fetch_parameter(
            'cross_account_access_role',
        )
        return remove_base(account_id, regions, privileged_role_name, event)
    return True


def lambda_handler(event, _):
    parameter_store = ParameterStore(REGION_DEFAULT, boto3)
    action = parameter_store.fetch_parameter_accept_not_found(
        name='moves/to_root/action',
        default_value='safe',
    )

    account_id = event.get('account_id')
    execute_move_action(action, account_id, parameter_store, event)

    return event
