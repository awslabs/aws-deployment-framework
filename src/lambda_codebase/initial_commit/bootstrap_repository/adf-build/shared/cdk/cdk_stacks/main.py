# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This is the main construct file file for PipelineStack
"""

from aws_cdk import (
    core
)
from cdk_constructs import adf_notifications
from logger import configure_logger

from .adf_standard_pipelines import generate_adf_pipeline, PIPELINE_TYPE as DEFAULT_PIPELINE

LOGGER = configure_logger(__name__)

class PipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, stack_input: dict, **kwargs) -> None: #pylint: disable=R0912, R0915
        super().__init__(scope, stack_input['input']['name'], **kwargs)
        LOGGER.info('Pipeline creation/update of %s commenced', stack_input['input']['name'])

        _pipeline_type = stack_input['input'].get('params', {}).get('pipeline_type', DEFAULT_PIPELINE).lower()

        if stack_input['input'].get('params', {}).get('notification_endpoint'):
            stack_input['input']["topic_arn"] = adf_notifications.Notifications(self, 'adf_notifications', stack_input['input']).topic_arn

        self.generate_pipeline(_pipeline_type, stack_input)

    def generate_pipeline(self, _pipeline_type, stack_input):
        _source_name = stack_input['input']["default_providers"]["source"]["provider"].lower()
        _build_name = stack_input['input']["default_providers"]["build"]["provider"].lower()

        if _pipeline_type == DEFAULT_PIPELINE:
            generate_adf_pipeline(self, _build_name, _source_name, stack_input)
        else:
            ValueError(f'{_pipeline_type} is not defined in main.py')
