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

from cdk_constructs import adf_codepipeline

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]
ADF_DEFAULT_SOURCE_ROLE = os.environ["ADF_DEFAULT_SOURCE_ROLE"]
ADF_DEFAULT_BUILD_ROLE = os.environ["ADF_DEFAULT_BUILD_ROLE"]
ADF_DEFAULT_BUILD_TIMEOUT = 20


class CloudFormation(core.Construct):
    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)

    @staticmethod
    def generate_actions(targets, region, map_params):
        _actions = []
        if not isinstance(targets, list):
            targets = [targets]
        for target in targets:
            _actions.append(
                adf_codepipeline.Action(
                    name="{0}-{1}-create".format(target['name'], region),
                    provider="CloudFormation",
                    category="Deploy",
                    region=region,
                    target=target,
                    run_order=1,
                    action_mode="CHANGE_SET_REPLACE",
                    map_params=map_params,
                    action_name="{0}-{1}-create".format(target['name'], region)
                ).config,
            )
            if target.get('change_set'):
                _actions.append(
                    adf_codepipeline.Action(
                        name="{0}-{1}".format(target['name'], region),
                        provider="Manual",
                        category="Approval",
                        region=region,
                        target=target,
                        run_order=2,
                        map_params=map_params,
                        action_name="{0}-{1}".format(target['name'], region)
                    ).config
                )
            _actions.append(
                adf_codepipeline.Action(
                    name="{0}-{1}-execute".format(target['name'], region),
                    provider="CloudFormation",
                    category="Deploy",
                    region=region,
                    target=target,
                    run_order=3 if target.get('change_set') else 2,
                    action_mode="CHANGE_SET_EXECUTE",
                    map_params=map_params,
                    action_name="{0}-{1}-execute".format(target['name'], region)
                ).config
            )
        return _actions