# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This is the main construct file file for PipelineStack
"""

from aws_cdk import (
    core
)
from cdk_constructs import adf_notifications, adf_chatbot
from logger import configure_logger

from cdk_stacks.adf_default_pipeline import generate_adf_default_pipeline as generate_default_pipeline, PIPELINE_TYPE as DEFAULT_PIPELINE

LOGGER = configure_logger(__name__)


class PipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, stack_input: dict, **kwargs) -> None: #pylint: disable=R0912, R0915
        super().__init__(scope, stack_input['input']['name'], **kwargs)
        LOGGER.info('Pipeline creation/update of %s commenced', stack_input['input']['name'])
        _pipeline_type = stack_input['input'].get('params', {}).get('type', DEFAULT_PIPELINE).lower()
        notification_config = stack_input["input"].get("params", {}).get("notification_endpoint", {})
        if isinstance(notification_config, str) or notification_config.get('type', '') == "lambda":
            stack_input["input"]["topic_arn"] = adf_notifications.Notifications(self, "adf_notifications", stack_input["input"]).topic_arn

        pipeline = self.generate_pipeline(_pipeline_type, stack_input).cfn
        if isinstance(notification_config, dict) and notification_config.get('type', '') == 'chat_bot':
            adf_chatbot.PipelineNotifications(self, "adf_chatbot_notifications", pipeline, notification_config)
    def generate_pipeline(self, _pipeline_type, stack_input):
        if _pipeline_type == DEFAULT_PIPELINE:
            return generate_default_pipeline(self, stack_input)

        raise ValueError(f'{_pipeline_type} is not defined in main.py')
