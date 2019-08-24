import os
from aws_cdk import (
    aws_codepipeline as _codepipeline,
    core
)

from cdk_constructs.adf_codepipeline import Action

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]
ADF_DEFAULT_SOURCE_ROLE = os.environ["ADF_DEFAULT_SOURCE_ROLE"]
ADF_DEFAULT_BUILD_ROLE = os.environ["ADF_DEFAULT_BUILD_ROLE"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20


class CodeCommit(core.Construct):
    def __init__(self, scope: core.Construct, id: str, map_params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.source = _codepipeline.CfnPipeline.StageDeclarationProperty(
                            name="Source-{0}".format(map_params.get("type", {}).get("source", {}).get("account_id", ADF_DEPLOYMENT_ACCOUNT_ID)),
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