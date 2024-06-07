# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

"""
Checks if legacy specific legacy bootstrap stacks exists.
If they do, they are cleaned up automatically.
"""

import os

import boto3
from cfn_custom_resource import (  # pylint: disable=unused-import
    lambda_handler,
    create,
    update,
    delete,
)

from cloudformation import CloudFormation, StackProperties
from logger import configure_logger

ACCOUNT_ID = os.environ["MANAGEMENT_ACCOUNT_ID"]
DEPLOYMENT_REGION = os.environ["DEPLOYMENT_REGION"]
ADF_GLOBAL_ADF_BUILD_STACK_NAME = 'adf-global-base-adf-build'

LOGGER = configure_logger(__name__)


def delete_adf_build_stack():
    cloudformation = CloudFormation(
        region=DEPLOYMENT_REGION,
        deployment_account_region=DEPLOYMENT_REGION,
        role=boto3,
        stack_name=ADF_GLOBAL_ADF_BUILD_STACK_NAME,
        wait=True,
        account_id=ACCOUNT_ID,
    )
    LOGGER.debug(
        '%s in %s - Checking if stack exists: %s',
        ACCOUNT_ID,
        DEPLOYMENT_REGION,
        ADF_GLOBAL_ADF_BUILD_STACK_NAME,
    )
    stack_status = cloudformation.get_stack_status()
    if cloudformation.get_stack_status():
        if stack_status not in StackProperties.clean_stack_status:
            raise RuntimeError(
                'Please remove stack %s in %s manually, state %s implies that '
                'it cannot be deleted automatically. ADF cannot be installed '
                'or updated until this stack is removed.',
                ADF_GLOBAL_ADF_BUILD_STACK_NAME,
                DEPLOYMENT_REGION,
                stack_status,
            )

        cloudformation.delete_stack(
            stack_name=ADF_GLOBAL_ADF_BUILD_STACK_NAME,
        )
        LOGGER.debug(
            '%s in %s - Stack deleted successfully: %s',
            ACCOUNT_ID,
            DEPLOYMENT_REGION,
            ADF_GLOBAL_ADF_BUILD_STACK_NAME,
        )
    else:
        LOGGER.debug(
            '%s in %s - Stack does not exist: %s',
            ACCOUNT_ID,
            DEPLOYMENT_REGION,
            ADF_GLOBAL_ADF_BUILD_STACK_NAME,
        )


@create()
def create_(event, _context):
    delete_adf_build_stack()
    return event.get("PhysicalResourceId"), {}


@update()
def update_(event, _context):
    delete_adf_build_stack()
    return event.get("PhysicalResourceId"), {}


@delete()
def delete_(_event, _context):
    pass
