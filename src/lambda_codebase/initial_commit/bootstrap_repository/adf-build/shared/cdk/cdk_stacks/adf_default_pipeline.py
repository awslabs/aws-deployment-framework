# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This is the functionality for generating a default adf pipeline.
"""

import os

from aws_cdk import aws_codepipeline as _codepipeline, core
from cdk_constructs import adf_codepipeline
from cdk_constructs import adf_codebuild
from cdk_constructs import adf_jenkins
from cdk_constructs import adf_codecommit
from cdk_constructs import adf_github
from cdk_constructs import adf_codestar
from cdk_constructs import adf_s3
from cdk_constructs import adf_cloudformation
from cdk_constructs import adf_notifications
from cdk_constructs import adf_chatbot
from logger import configure_logger

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20
LOGGER = configure_logger(__name__)

PIPELINE_TYPE = "default"


def generate_adf_default_pipeline(scope: core.Stack, stack_input):
    _stages = []

    notification_config = stack_input["input"].get("params", {}).get("notification_endpoint", {})

    if isinstance(notification_config, str) or notification_config.get('type', '') == "lambda":
        stack_input["input"]["topic_arn"] = adf_notifications.Notifications(scope, "adf_notifications", stack_input["input"]).topic_arn

    _source_name = generate_source_stage_for_pipeline(_stages, scope, stack_input)
    generate_build_stage_for_pipeline(_stages, scope, stack_input)
    generate_targets_for_pipeline(_stages, scope, stack_input)

    _pipeline = adf_codepipeline.Pipeline(
        scope, "code_pipeline", stack_input["input"], stack_input["ssm_params"], _stages
    )

    if "github" in _source_name:
        adf_github.GitHub.create_webhook_when_required(scope, _pipeline.cfn, stack_input["input"])

    pipeline_triggers = stack_input["input"].get("triggers", {}).get("triggered_by")
    if pipeline_triggers:
        for trigger_type, trigger_config in pipeline_triggers.items():
            _pipeline.add_pipeline_trigger(trigger_type=trigger_type, trigger_config=trigger_config)

    if isinstance(notification_config, dict) and notification_config.get('type', '') == 'chat_bot':
        adf_chatbot.PipelineNotifications(scope, "adf_chatbot_notifications", _pipeline.cfn, notification_config)


def generate_source_stage_for_pipeline(_stages, scope, stack_input):
    _source_name = stack_input["input"]["default_providers"]["source"][
        "provider"
    ].lower()
    if "codecommit" in _source_name:
        _stages.append(
            adf_codecommit.CodeCommit(scope, "source", stack_input["input"]).source
        )
    elif "codestar" in _source_name:
        _stages.append(adf_codestar.CodeStar(scope, "source", stack_input['input']).source)
    elif "github" in _source_name:
        _stages.append(adf_github.GitHub(scope, "source", stack_input["input"]).source)
    elif "s3" in _source_name:
        _stages.append(adf_s3.S3(scope, "source", stack_input["input"]).source)
    return _source_name


def generate_build_stage_for_pipeline(_stages, scope, stack_input):
    _build_name = (
        stack_input["input"]["default_providers"]["build"].get("provider", "").lower()
    )
    build_enabled = stack_input["input"]["default_providers"]["build"].get("enabled", True)
    if "codebuild" in _build_name and build_enabled:
        _stages.append(
            adf_codebuild.CodeBuild(
                scope,
                "build",
                stack_input["ssm_params"][ADF_DEPLOYMENT_REGION]["modules"],
                stack_input["ssm_params"][ADF_DEPLOYMENT_REGION]["kms"],
                stack_input["input"],
                {},  # Empty target since this is a build only stage
            ).build
        )
    elif "jenkins" in _build_name:
        _stages.append(adf_jenkins.Jenkins(scope, "build", stack_input["input"]).build)


def generate_targets_for_pipeline(_stages, scope, stack_input):
    for index, targets in enumerate(
            stack_input["input"].get("environments", {}).get("targets", [])
    ):

        top_level_deployment_type = (
            stack_input["input"]
            .get("default_providers", {})
            .get("deploy", {})
            .get("provider", "")
            or "cloudformation"
        )
        top_level_action = (
            stack_input["input"]
            .get("default_providers", {})
            .get("deploy", {})
            .get("properties", {})
            .get("action", "")
        )

        for wave_index, wave in enumerate(targets):
            _actions = []
            _is_approval = (
                wave[0].get("name", "").startswith("approval")
                or wave[0].get("provider", "") == "approval"
            )
            _action_type_name = "approval" if _is_approval else "deployment"
            _stage_name = (
                # 0th Index since step names are for entire stages not
                # per target.
                f"{wave[0].get('step_name')}-{wave_index}"
                if wave[0].get("step_name") else f"{_action_type_name}-stage-{index + 1}-wave-{wave_index}"
            )

            for target in wave:
                target_stage_override = target.get("provider") or top_level_deployment_type
                if target.get("name") == "approval" or target.get("provider", "") == "approval":
                    _actions.extend(
                        [
                            adf_codepipeline.Action(
                                name=f"wave-{wave_index}-{target.get('name')}".format(target["name"]),
                                provider="Manual",
                                category="Approval",
                                target=target,
                                run_order=1,
                                map_params=stack_input["input"],
                                action_name=f"{target.get('name')}",
                            ).config
                        ]
                    )
                    continue

                if "codebuild" in target_stage_override:
                    _actions.extend(
                        [
                            adf_codebuild.CodeBuild(
                                scope,
                                # Use the name of the pipeline for CodeBuild
                                # instead of the target name as it will always
                                # operate from the deployment account.
                                f"{stack_input['input']['name']}-target-{index + 1}-wave-{wave_index}",
                                stack_input["ssm_params"][ADF_DEPLOYMENT_REGION]["modules"],
                                stack_input["ssm_params"][ADF_DEPLOYMENT_REGION]["kms"],
                                stack_input["input"],
                                target,
                            ).deploy
                        ]
                    )
                    continue

                regions = target.get("regions", [])
                generate_deployment_action_per_region(
                    _actions,
                    regions,
                    stack_input,
                    target,
                    target_stage_override,
                    top_level_action,
                )

            _stages.append(
                _codepipeline.CfnPipeline.StageDeclarationProperty(
                    name=_stage_name,
                    actions=_actions,
                )
            )


def generate_deployment_action_per_region(_actions,
                                          regions,
                                          stack_input,
                                          target,
                                          target_stage_override,
                                          top_level_action
                                          ):
    for region in regions:
        if "cloudformation" in target_stage_override:
            target_approval_mode = target.get("properties", {}).get(
                "change_set_approval", False
            )
            _target_action_mode = target.get("properties", {}).get("action")
            action_mode = _target_action_mode or top_level_action
            if action_mode:
                _actions.extend(
                    [
                        adf_codepipeline.Action(
                            name=f"{target['name']}-{region}",
                            provider="CloudFormation",
                            category="Deploy",
                            region=region,
                            target=target,
                            action_mode=action_mode,
                            run_order=1,
                            map_params=stack_input["input"],
                            action_name=f"{target['name']}-{region}",
                        ).config
                    ]
                )
                continue
            _actions.extend(
                adf_cloudformation.CloudFormation.generate_actions(
                    target, region, stack_input["input"], target_approval_mode
                )
            )
        elif "codedeploy" in target_stage_override:
            _actions.extend(
                [
                    adf_codepipeline.Action(
                        name=f"{target['name']}-{region}",
                        provider="CodeDeploy",
                        category="Deploy",
                        region=region,
                        target=target,
                        action_mode=top_level_action,
                        run_order=1,
                        map_params=stack_input["input"],
                        action_name=f"{target['name']}-{region}",
                    ).config
                ]
            )
        elif "s3" in target_stage_override:
            _actions.extend(
                [
                    adf_codepipeline.Action(
                        name=f"{target['name']}-{region}",
                        provider="S3",
                        category="Deploy",
                        region=region,
                        target=target,
                        action_mode=top_level_action,
                        run_order=1,
                        map_params=stack_input["input"],
                        action_name=f"{target['name']}-{region}",
                    ).config
                ]
            )
        elif "lambda" in target_stage_override:
            _actions.extend(
                [
                    adf_codepipeline.Action(
                        name=f"{target['name']}-{region}",
                        provider="Lambda",
                        category="Invoke",
                        region=region,
                        target=target,
                        action_mode=top_level_action,
                        run_order=1,
                        map_params=stack_input["input"],
                        action_name=f"{target['name']}-{region}",
                    ).config
                ]
            )
        elif "service_catalog" in target_stage_override:
            _actions.extend(
                [
                    adf_codepipeline.Action(
                        name=f"{target['name']}-{region}",
                        provider="ServiceCatalog",
                        category="Deploy",
                        region=region,
                        target=target,
                        action_mode=top_level_action,
                        run_order=1,
                        map_params=stack_input["input"],
                        action_name=f"{target['name']}-{region}",
                    ).config
                ]
            )
