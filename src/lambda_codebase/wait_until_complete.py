# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Awaits the CloudFormation stacks to reach their intended
end state. This will raise a RetryError while the stack
has not yet reached its intended state. This will
cause Step Functions to retry this stage until the requirements
are met.
"""

import os

from sts import STS
from s3 import S3
from parameter_store import ParameterStore
from errors import RetryError
from logger import configure_logger
from cloudformation import CloudFormation

S3_BUCKET = os.environ["S3_BUCKET_NAME"]
REGION_DEFAULT = os.environ["AWS_REGION"]
LOGGER = configure_logger(__name__)


def update_deployment_account_output_parameters(
        deployment_account_region,
        region,
        deployment_account_role,
        cloudformation):

    deployment_account_parameter_store = ParameterStore(
        deployment_account_region, deployment_account_role
    )
    regional_parameter_store = ParameterStore(
        region, deployment_account_role
    )
    # Regions needs to know to organization ID for Bucket Policy
    regional_parameter_store.put_parameter(
        "organization_id", os.environ['ORGANIZATION_ID']
    )
    # Regions needs to store its kms arn and s3 bucket in master and regional
    for key, value in cloudformation.get_stack_regional_outputs().items():
        LOGGER.info('Updating %s on deployment account in %s', key, region)
        deployment_account_parameter_store.put_parameter(
            "/cross_region/{0}/{1}".format(key, region),
            value
        )
        regional_parameter_store.put_parameter(
            "/cross_region/{0}/{1}".format(key, region),
            value
        )


def lambda_handler(event, _):
    """Main Lambda Entry point
    """
    sts = STS()

    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            event['account_id'],
            event['cross_account_access_role'],
        ),
        'master'
    )

    s3 = S3(REGION_DEFAULT, S3_BUCKET)

    for region in list(set([event['deployment_account_region']] + event['regions'])):

        cloudformation = CloudFormation(
            region=region,
            deployment_account_region=event['deployment_account_region'],
            role=role,
            wait=False,
            stack_name=None,
            s3=s3,
            s3_key_path=event['ou_name'],
            account_id=event['account_id']
        )

        status = cloudformation.get_stack_status()

        if status in ('CREATE_IN_PROGRESS', 'UPDATE_IN_PROGRESS'):
            raise RetryError("Cloudformation Stack is {0}".format(status))

        if status in (
                'CREATE_FAILED',
                'ROLLBACK_FAILED',
                'DELETE_FAILED',
                'UPDATE_ROLLBACK_FAILED',
                'ROLLBACK_IN_PROGRESS',
                'ROLLBACK_COMPLETE'
            ):
            raise Exception("Account Bootstrap Failed - Account: {0} Region: {1} Status: {2}".format(
                event['account_id'],
                region,
                status))

        if event.get('is_deployment_account'):
            update_deployment_account_output_parameters(
                deployment_account_region=event['deployment_account_region'],
                region=region,
                deployment_account_role=role,
                cloudformation=cloudformation
            )

    return event
