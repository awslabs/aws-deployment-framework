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
    ).get('status')

    if pipeline_status == 'Failed':
        LOGGER.info(
            'aws-deployment-framework-pipelines is in a failed state. Exiting.'
        )
        return event

    if not pipeline_status == 'InProgress':
        codepipeline.start_pipeline_execution(
            'aws-deployment-framework-pipelines'
        )
        LOGGER.info(
            'aws-deployment-framework-pipelines is already running'
        )

    return event
