# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to Notifications Codepipeline Input
"""

import os
from aws_cdk import (
    aws_lambda as _lambda,
    aws_sns as _sns,
    aws_iam as _iam,
    aws_kms as _kms,
    aws_lambda_event_sources as _event_sources,
    core
)
from logger import configure_logger

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]

LOGGER = configure_logger(__name__)


class Notifications(core.Construct):
    def __init__(
        self, scope: core.Construct, id: str, map_params: dict, **kwargs
    ):  # pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        LOGGER.debug('Notification configuration required for %s', map_params['name'])
        stack = core.Stack.of(self)
        # pylint: disable=no-value-for-parameter
        _slack_func = _lambda.Function.from_function_arn(
            self,
            'slack_lambda_function',
            f'arn:{stack.partition}:lambda:{ADF_DEPLOYMENT_REGION}:'
            f'{ADF_DEPLOYMENT_ACCOUNT_ID}:function:SendSlackNotification'
        )
        kms_alias = _kms.Alias.from_alias_name(self, "KMSAlias", f"alias/codepipeline-{ADF_DEPLOYMENT_ACCOUNT_ID}")
        _topic = _sns.Topic(self, "PipelineTopic", master_key=kms_alias)
        _statement = _iam.PolicyStatement(
            actions=["sns:Publish"],
            effect=_iam.Effect.ALLOW,
            principals=[
                _iam.ServicePrincipal("sns.amazonaws.com"),
                _iam.ServicePrincipal("codecommit.amazonaws.com"),
                _iam.ServicePrincipal("events.amazonaws.com"),
            ],
            resources=["*"],
        )
        _topic.add_to_resource_policy(_statement)
        _endpoint = map_params.get("params", {}).get("notification_endpoint", "")
        _sub = _sns.Subscription(
            self,
            "sns_subscription",
            topic=_topic,
            endpoint=_endpoint if "@" in _endpoint else _slack_func.function_arn,
            protocol=_sns.SubscriptionProtocol.EMAIL
            if "@" in _endpoint
            else _sns.SubscriptionProtocol.LAMBDA,
        )
        if "@" not in _endpoint:
            _lambda.CfnPermission(
                self,
                "slack_notification_sns_permissions",
                principal="sns.amazonaws.com",
                action="lambda:InvokeFunction",
                source_arn=_topic.topic_arn,
                function_name="SendSlackNotification",
            )
            _slack_func.add_event_source(source=_event_sources.SnsEventSource(_topic))
        self.topic_arn = _topic.topic_arn
