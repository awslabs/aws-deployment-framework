# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to Notifications Codepipeline Input
"""

import os
from aws_cdk import (
    aws_codestarnotifications as cp_notifications,
    aws_codepipeline as codepipeline,
    core,
)
from logger import configure_logger

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]

LOGGER = configure_logger(__name__)

EVENT_TYPE_IDS = [
    "codepipeline-pipeline-stage-execution-succeeded",
    "codepipeline-pipeline-stage-execution-failed",
    "codepipeline-pipeline-pipeline-execution-started",
    "codepipeline-pipeline-pipeline-execution-failed",
    "codepipeline-pipeline-pipeline-execution-succeeded",
    "codepipeline-pipeline-manual-approval-needed",
    "codepipeline-pipeline-manual-approval-succeeded",
]


class PipelineNotifications(core.Construct):
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        pipeline: codepipeline.CfnPipeline,
        notification_config,
        **kwargs,
    ):  # pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        slack_channel_arn = f"arn:aws:chatbot::{ADF_DEPLOYMENT_ACCOUNT_ID}:chat-configuration/slack-channel/{notification_config.get('target')}"
        pipeline_arn = f"arn:aws:codepipeline:{ADF_DEPLOYMENT_REGION}:{ADF_DEPLOYMENT_ACCOUNT_ID}:{pipeline.ref}"
        cp_notifications.CfnNotificationRule(
            scope,
            "pipeline-notification",
            detail_type="FULL",
            event_type_ids=EVENT_TYPE_IDS,
            name=pipeline.ref,
            resource=pipeline_arn,
            targets=[
                cp_notifications.CfnNotificationRule.TargetProperty(
                    target_type=PipelineNotifications.get_target_type_from_config(
                        scope, notification_config
                    ),
                    target_address=slack_channel_arn,
                )
            ],
        )

    @staticmethod
    def get_target_type_from_config(scope, config):
        target_type = config.get("type", "chat_bot")
        if target_type == "chat_bot":
            return "AWSChatbotSlack"
        scope.node.add_error(
            f"{target_type} is not supported for CodePipeline notifications."
        )
        return None
