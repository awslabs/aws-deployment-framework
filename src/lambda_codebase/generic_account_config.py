# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


"""
Executes for any account that has been
Bootstrapped other than the Deployment Account
This step is responsible for starting the execution
of the State Machine on the Deployment Account
To Update the IAM Role, KMS Policy and S3 Bucket Policy
To include the newly created account.
"""

from logger import configure_logger
from sts import STS
from stepfunctions import StepFunctions

LOGGER = configure_logger(__name__)


def lambda_handler(event, _):
    sts = STS()

    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            event['deployment_account_id'],
            event['cross_account_access_role']),
        'step_function')

    step_functions = StepFunctions(
        role=role,
        deployment_account_id=event['deployment_account_id'],
        deployment_account_region=event['deployment_account_region'],
        full_path=event['full_path'],
        regions=event['regions'],
        account_ids=[event['account_id']],
        update_pipelines_only=1 if event.get('moved_to_protected') or event.get('moved_to_root') else 0,
        error=event.get('error', 0)
    )
    step_functions.execute_statemachine()

    return event
