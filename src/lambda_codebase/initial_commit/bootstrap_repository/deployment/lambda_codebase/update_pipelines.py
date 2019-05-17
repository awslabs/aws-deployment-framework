# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
update_pipelines.py is responsible for starting the
aws-deployment-framework-pipelines pipeline if
it is not already executing or failed
"""

import os
import boto3
from logger import configure_logger
from codepipeline import CodePipeline

LOGGER = configure_logger(__name__)


def generate_notify_message(event):
    """
    The message we want to pass into the next step (Notify) of the state machine
    if the current account in execution has been bootstrapped
    """
    update_status = event.get('update_only', 1)
    if len(event.get('account_ids')) > 1:
        update_status = 1
    return {
        "update_only": update_status,
        "message": "Account {0} has now been bootstrapped into {1}".format(event["account_ids"][0], event["full_path"])
    }

def lambda_handler(event, _):
    """
    Responsible for triggering the aws-deployment-framework-pipelines
    pipeline if its not already running
    """
    codepipeline = CodePipeline(
        boto3,
        os.environ['AWS_REGION']
    )

    pipeline_status = codepipeline.get_pipeline_status(
        'aws-deployment-framework-pipelines'
    )

    if pipeline_status in ('Failed', 'InProgress'):
        LOGGER.info(
            'aws-deployment-framework-pipelines is in %s. Exiting.',
            pipeline_status
        )
        return generate_notify_message(event)

    codepipeline.start_pipeline_execution(
        'aws-deployment-framework-pipelines'
    )

    return generate_notify_message(event)
