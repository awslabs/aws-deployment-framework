# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This is the main construct file file for PipelineStack
"""

import os

from aws_cdk import (
    aws_codepipeline as _codepipeline,
    core
)
from cdk_constructs import adf_codepipeline
from cdk_constructs import adf_codebuild
from cdk_constructs import adf_jenkins
from cdk_constructs import adf_codecommit
from cdk_constructs import adf_github
from cdk_constructs import adf_s3
from cdk_constructs import adf_cloudformation
from cdk_constructs import adf_notifications
from logger import configure_logger

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20
LOGGER = configure_logger(__name__)

class PipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, stack_input: dict, **kwargs) -> None: #pylint: disable=R0912, R0915
        super().__init__(scope, stack_input['input']['name'], **kwargs)
        LOGGER.info('Pipeline creation/update of %s commenced', stack_input['input']['name'])
        _source_name = stack_input['input']["default_providers"]["source"]["provider"].lower()
        _build_name = stack_input['input']["default_providers"]["build"].get("provider", '').lower()
        _stages = []
        if stack_input['input'].get('params', {}).get('notification_endpoint'):
            stack_input['input']["topic_arn"] = adf_notifications.Notifications(self, 'adf_notifications', stack_input['input']).topic_arn
        if 'codecommit' in _source_name:
            _stages.append(
                adf_codecommit.CodeCommit(
                    self,
                    'source',
                    stack_input['input']
                ).source
            )
        elif 'github' in _source_name:
            _stages.append(
                adf_github.GitHub(
                    self,
                    'source',
                    stack_input['input']
                ).source
            )
        elif 's3' in _source_name:
            _stages.append(
                adf_s3.S3(
                    self,
                    'source',
                    stack_input['input']
                ).source
            )
        if 'codebuild' in _build_name and stack_input["input"]["default_providers"]["build"].get('enabled', True):
            _stages.append(
                adf_codebuild.CodeBuild(
                    self,
                    'build',
                    stack_input['ssm_params'][ADF_DEPLOYMENT_REGION]["modules"],
                    stack_input['ssm_params'][ADF_DEPLOYMENT_REGION]["kms"],
                    stack_input['input'],
                    {} # Empty target since this is a build only stage
                ).build
            )
        elif 'jenkins' in _build_name:
            _stages.append(
                adf_jenkins.Jenkins(
                    self,
                    'build',
                    stack_input['input']
                ).build
            )
        for index, targets in enumerate(stack_input['input'].get('environments', {}).get('targets', [])):
            _actions = []
            top_level_deployment_type = stack_input['input'].get('default_providers', {}).get('deploy', {}).get('provider', '') or 'cloudformation'
            top_level_action = stack_input['input'].get('default_providers', {}).get('deploy', {}).get('properties', {}).get('action', '')
            for target in targets:
                target_stage_override = target.get('provider') or top_level_deployment_type
                if target.get('name') == 'approval' or target.get('provider', '') == 'approval':
                    _actions.extend([
                        adf_codepipeline.Action(
                            name="{0}".format(target['name']),
                            provider="Manual",
                            category="Approval",
                            target=target,
                            run_order=1,
                            map_params=stack_input['input'],
                            action_name="{0}".format(target['name'])
                        ).config
                    ])
                    continue
                elif 'codebuild' in target_stage_override:
                    _actions.extend([
                        adf_codebuild.CodeBuild(
                            self,
                            # Use the name of the pipeline for CodeBuild
                            # instead of the target name as it will always
                            # operate from the deployment account.
                            "{pipeline_name}-stage-{index}".format(
                                pipeline_name=stack_input['input']['name'],
                                index=index + 1,
                            ),
                            stack_input['ssm_params'][ADF_DEPLOYMENT_REGION]["modules"],
                            stack_input['ssm_params'][ADF_DEPLOYMENT_REGION]["kms"],
                            stack_input['input'],
                            target
                        ).deploy
                    ])
                    continue
                regions = target.get('regions', [])
                for region in regions:
                    if 'cloudformation' in target_stage_override:
                        target_approval_mode = target.get('properties', {}).get('change_set_approval', False)
                        _target_action_mode = target.get('properties', {}).get('action')
                        action_mode = _target_action_mode or top_level_action
                        if action_mode:
                            _actions.extend([
                                adf_codepipeline.Action(
                                    name="{0}-{1}".format(target['name'], region),
                                    provider="CloudFormation",
                                    category="Deploy",
                                    region=region,
                                    target=target,
                                    action_mode=action_mode,
                                    run_order=1,
                                    map_params=stack_input['input'],
                                    action_name="{0}-{1}".format(target['name'], region)
                                ).config
                            ])
                            continue
                        _actions.extend(adf_cloudformation.CloudFormation.generate_actions(target, region, stack_input['input'], target_approval_mode))
                    elif 'codedeploy' in target_stage_override:
                        _actions.extend([
                            adf_codepipeline.Action(
                                name="{0}-{1}".format(target['name'], region),
                                provider="CodeDeploy",
                                category="Deploy",
                                region=region,
                                target=target,
                                action_mode=top_level_action,
                                run_order=1,
                                map_params=stack_input['input'],
                                action_name="{0}-{1}".format(target['name'], region)
                            ).config
                        ])
                    elif 's3' in target_stage_override:
                        _actions.extend([
                            adf_codepipeline.Action(
                                name="{0}-{1}".format(target['name'], region),
                                provider="S3",
                                category="Deploy",
                                region=region,
                                target=target,
                                action_mode=top_level_action,
                                run_order=1,
                                map_params=stack_input['input'],
                                action_name="{0}-{1}".format(target['name'], region)
                            ).config
                        ])
                    elif 'lambda' in target_stage_override:
                        _actions.extend([
                            adf_codepipeline.Action(
                                name="{0}-{1}".format(target['name'], region),
                                provider="Lambda",
                                category="Invoke",
                                region=region,
                                target=target,
                                action_mode=top_level_action,
                                run_order=1,
                                map_params=stack_input['input'],
                                action_name="{0}-{1}".format(target['name'], region)
                            ).config
                        ])
                    elif 'service_catalog' in target_stage_override:
                        _actions.extend([
                            adf_codepipeline.Action(
                                name="{0}-{1}".format(target['name'], region),
                                provider="ServiceCatalog",
                                category="Deploy",
                                region=region,
                                target=target,
                                action_mode=top_level_action,
                                run_order=1,
                                map_params=stack_input['input'],
                                action_name="{0}-{1}".format(target['name'], region)
                            ).config
                        ])
            _is_approval = targets[0].get('name', '').startswith('approval') or \
                    targets[0].get('provider', '') == 'approval'
            _action_type_name = 'approval' if _is_approval else 'deployment'
            _stage_name = (
                # 0th Index since step names are for entire stages not
                # per target.
                targets[0].get('step_name') or
                '{action_type_name}-stage-{index}'.format(
                    action_type_name=_action_type_name,
                    index=index + 1,
                )
            )
            _stages.append(
                _codepipeline.CfnPipeline.StageDeclarationProperty(
                    name=_stage_name,
                    actions=_actions,
                )
            )
        _pipeline = adf_codepipeline.Pipeline(self, 'code_pipeline', stack_input['input'], stack_input['ssm_params'], _stages)
        if 'github' in _source_name:
            adf_github.GitHub.create_webhook(self, _pipeline.cfn, stack_input['input'])
