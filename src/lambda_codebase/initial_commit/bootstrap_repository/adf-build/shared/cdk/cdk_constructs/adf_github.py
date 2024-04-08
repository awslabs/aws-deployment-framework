# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""Construct related to Github Codepipeline Input
"""

import os

from aws_cdk import (
    aws_codepipeline as _codepipeline,
    Token,
)
from constructs import Construct

from cdk_constructs.adf_codepipeline import Action

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20


class GitHub(Construct):
    def __init__(self, scope: Construct, id: str, map_params: dict, **kwargs): #pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        self.source = _codepipeline.CfnPipeline.StageDeclarationProperty(
            name="Source-Github",
            actions=[
                Action(
                    name="source",
                    provider="GitHub",
                    owner="ThirdParty",
                    category="Source",
                    run_order=1,
                    map_params=map_params,
                    action_name="source"
                ).config
            ]
        )

    @staticmethod
    def create_webhook_when_required(scope, pipeline, map_params):
        trigger_on_changes = map_params.get("default_providers", {}).get(
            "source", {}).get("properties", {}).get("trigger_on_changes", True)
        if not trigger_on_changes:
            return

        pipeline_version = pipeline.get_att('Version')
        branch_name = (
            (
                map_params
                .get('default_providers', {})
                .get('source', {})
                .get('properties', {})
                .get('branch')
            )
            or 'main'
        )
        _codepipeline.CfnWebhook(
            scope,
            'github_webhook',
            authentication_configuration=_codepipeline.CfnWebhook.WebhookAuthConfigurationProperty(
                # We can't have a randomly generated string here as it could
                # update and change its value frequently
                secret_token=map_params['name']
            ),
            authentication="GITHUB_HMAC",
            target_pipeline=pipeline.ref,
            filters=[
                _codepipeline.CfnWebhook.WebhookFilterRuleProperty(
                    json_path="$.ref",
                    match_equals=f"refs/heads/{branch_name}",
                )
            ],
            target_action="source",
            name=f"adf-webhook-{map_params['name']}",
            # pylint: disable=no-value-for-parameter
            target_pipeline_version=Token.as_number(pipeline_version),
            register_with_third_party=True
        )
