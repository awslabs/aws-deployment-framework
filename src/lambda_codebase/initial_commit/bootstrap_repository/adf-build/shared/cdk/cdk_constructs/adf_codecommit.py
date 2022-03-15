# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to CodeCommit Input
"""

import os
from aws_cdk import (
    aws_codepipeline as _codepipeline,
    core
)

from cdk_constructs.adf_codepipeline import Action

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20


class CodeCommit(core.Construct):
    def __init__(self, scope: core.Construct, id: str, map_params: dict, **kwargs): #pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        default_providers = map_params.get("default_providers", {})
        source_props = default_providers.get("source", {}).get("properties", {})
        account_id = source_props.get("account_id", ADF_DEPLOYMENT_ACCOUNT_ID)
        self.source = _codepipeline.CfnPipeline.StageDeclarationProperty(
            name=f"Source-{account_id}",
            actions=[
                Action(
                    name="source",
                    provider="CodeCommit",
                    category="Source",
                    run_order=1,
                    map_params=map_params,
                    action_name="source"
                ).config
            ]
        )
