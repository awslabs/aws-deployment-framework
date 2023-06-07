# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to CodeCommit Input
"""

import os
from aws_cdk import (
    aws_codepipeline as _codepipeline,
)
from constructs import Construct

from cdk_constructs.adf_codepipeline import Action

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20

class CodeCommit(Construct):
    def __init__(self, scope: Construct, id: str, map_params: dict, **kwargs): #pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        default_providers = map_params.get("default_providers", {})
        source_props = default_providers.get("source", {}).get("properties", {})
        
        # Resolve account_id in case it is not set
        # Evaluate as follows: 
        # If account_id not set, we have to set it as follows:
        #   - set via default_scm_codecommit_account_id (if exists)
        #   - or set via ADF_DEPLOYMENT_ACCOUNT_ID
        default_scm_codecommit_account_id = map_params.get("default_scm_codecommit_account_id", "")
        if not source_props.get("account_id"):
            print("account_id not found in source_props - recreate it!")
            if default_scm_codecommit_account_id:
                account_id = default_scm_codecommit_account_id
            else:
                account_id = ADF_DEPLOYMENT_ACCOUNT_ID
            if "properties" in map_params["default_providers"]["source"]:
                # append to properties
                map_params["default_providers"]["source"]["properties"]["account_id"] = account_id
            else:
                # recreate properties
                source_props =  {
                    "account_id": account_id
                }
                map_params["default_providers"]["source"]["properties"] = source_props
        else:
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
