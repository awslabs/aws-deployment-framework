# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_codepipeline_actions as _codepipeline_actions,
    aws_codecommit as _codecommit,
    aws_codebuild as _codebuild,
    aws_s3 as _s3,
    aws_iam as _iam,
    aws_kms as _kms,
    aws_ssm as _ssm,
    core
)

from cdk_constructs.adf_codepipeline import Action

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]

class Jenkins(core.Construct):
    def __init__(self, scope: core.Construct, id: str, map_params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.build = _codepipeline.CfnPipeline.StageDeclarationProperty(
            name="Build",
            actions=[
                Action(
                    name="Build",
                    provider="Jenkins",
                    category="Build",
                    run_order=1,
                    map_params=map_params,
                    action_name="build"
                ).config
            ]
        )
