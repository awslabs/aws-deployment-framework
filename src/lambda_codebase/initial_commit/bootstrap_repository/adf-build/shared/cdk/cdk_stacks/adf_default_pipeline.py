# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This is the functionality for generating a default ADF pipeline.
"""

import os

from aws_cdk import aws_codepipeline as _codepipeline, Stack
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


def generate_adf_default_pipeline(scope: Stack, stack_input):
    stages = []

    notification_config = (
        stack_input["pipeline_input"]
        .get("params", {})
        .get("notification_endpoint", {})
    )

    needs_topic_arn = (
        isinstance(notification_config, str)
        or notification_config.get('type', '') == "lambda"
    )
    if needs_topic_arn:
        stack_input["pipeline_input"]["topic_arn"] = (
            adf_notifications.Notifications(
                scope,
                "adf_notifications",
                stack_input["pipeline_input"],
            ).topic_arn
        )

    source_stage = _generate_source_stage_for_pipeline(scope, stack_input)
    if source_stage is not None:
        stages.append(source_stage)

    build_stage = _generate_build_stage_for_pipeline(scope, stack_input)
    if build_stage is not None:
        stages.append(build_stage)

    stages.extend(
        _generate_stages_with_targets_for_pipeline(scope, stack_input)
    )

    pipeline = adf_codepipeline.Pipeline(
        scope, "code_pipeline",
        stack_input["pipeline_input"],
        stack_input["ssm_params"],
        stages,
    )

    if "github" in _get_source_name(stack_input):
        adf_github.GitHub.create_webhook_when_required(
            scope,
            pipeline.cfn,
            stack_input["pipeline_input"],
        )

    pipeline_triggers = (
        stack_input["pipeline_input"]
        .get("triggers", {})
        .get("triggered_by")
    )
    if pipeline_triggers:
        for trigger_type, trigger_config in pipeline_triggers.items():
            pipeline.add_pipeline_trigger(
                trigger_type=trigger_type,
                trigger_config=trigger_config,
            )

    needs_chatbot_notifications = (
        isinstance(notification_config, dict)
        and notification_config.get('type', '') == 'chat_bot'
    )
    if needs_chatbot_notifications:
        adf_chatbot.PipelineNotifications(
            scope,
            "adf_chatbot_notifications",
            pipeline.cfn,
            notification_config,
        )


def _get_source_name(stack_input):
    return (
        stack_input["pipeline_input"]["default_providers"]
        .get("source", {})
        .get("provider", "codecommit")
        .lower()
    )


def _generate_source_stage_for_pipeline(scope, stack_input):
    source_name = _get_source_name(stack_input)
    if "codecommit" in source_name:
        return adf_codecommit.CodeCommit(
            scope,
            "source",
            stack_input["pipeline_input"],
        ).source
    if "codestar" in source_name:
        return adf_codestar.CodeStar(
            scope,
            "source",
            stack_input['pipeline_input'],
        ).source
    if "github" in source_name:
        return adf_github.GitHub(
            scope,
            "source",
            stack_input["pipeline_input"],
        ).source
    if "s3" in source_name:
        return adf_s3.S3(
            scope,
            "source",
            stack_input["pipeline_input"],
        ).source
    return None


def _generate_build_stage_for_pipeline(scope, stack_input):
    build_enabled = (
        stack_input["pipeline_input"]["default_providers"]
        .get("build", {})
        .get("enabled", True)
    )
    if build_enabled is not True:
        return None

    build_name = (
        stack_input["pipeline_input"]["default_providers"]
        .get("build", {})
        .get("provider", "")
        .lower()
    )

    if "codebuild" in build_name:
        return adf_codebuild.CodeBuild(
            scope,
            "build",
            stack_input["ssm_params"][ADF_DEPLOYMENT_REGION]["modules"],
            stack_input["ssm_params"][ADF_DEPLOYMENT_REGION]["kms"],
            stack_input["deployment_map_source"],
            stack_input["deployment_map_name"],
            stack_input["pipeline_input"],
            {},  # Empty target since this is a build only stage
        ).build
    if "jenkins" in build_name:
        return adf_jenkins.Jenkins(
            scope,
            "build",
            stack_input["pipeline_input"],
        ).build
    return None


def _generate_stages_with_targets_for_pipeline(scope, stack_input):
    stages = []
    for index, targets in enumerate(
        stack_input["pipeline_input"]
        .get("environments", {})
        .get("targets", [])
    ):
        top_level_deployment_type = (
            stack_input["pipeline_input"]
            .get("default_providers", {})
            .get("deploy", {})
            .get("provider", "cloudformation")
        )
        top_level_action = (
            stack_input["pipeline_input"]
            .get("default_providers", {})
            .get("deploy", {})
            .get("properties", {})
            .get("action", "")
        )

        for wave_index, wave in enumerate(targets):
            actions = []
            is_approval = (
                wave[0].get("name", "").startswith("approval")
                or wave[0].get("provider", "") == "approval"
            )
            action_type_name = "approval" if is_approval else "deployment"
            stage_name = (
                # 0th Index since step names are for entire stages not
                # per target.
                f"{wave[0].get('step_name')}-{wave_index}"
                if wave[0].get("step_name")
                else f"{action_type_name}-stage-{index + 1}-wave-{wave_index}"
            )

            for target in wave:
                target_stage_override = (
                    target.get("provider", top_level_deployment_type)
                )
                is_approval = (
                    target.get("name") == "approval"
                    or target.get("provider", "") == "approval"
                )
                if is_approval:
                    actions.extend([
                        adf_codepipeline.Action(
                            name=f"wave-{wave_index}-{target.get('name')}",
                            provider="Manual",
                            category="Approval",
                            target=target,
                            run_order=1,
                            map_params=stack_input["pipeline_input"],
                            action_name=f"{target.get('name')}",
                        ).config
                    ])
                    continue

                if "codebuild" in target_stage_override:
                    deploy_params = (
                        stack_input["ssm_params"][ADF_DEPLOYMENT_REGION]
                    )
                    actions.extend([
                        adf_codebuild.CodeBuild(
                            scope,
                            # Use the name of the pipeline for CodeBuild
                            # instead of the target name as it will always
                            # operate from the deployment account.
                            (
                                f"{stack_input['pipeline_input']['name']}-"
                                f"target-{index + 1}-{target['id']}-wave-{wave_index}"
                            ),
                            deploy_params["modules"],
                            deploy_params["kms"],
                            stack_input["deployment_map_source"],
                            stack_input["deployment_map_name"],
                            stack_input["pipeline_input"],
                            target,
                        ).deploy
                    ])
                    continue

                regions = target.get("regions", [])
                actions.extend(
                    # Returns a list of actions:
                    _generate_deployment_action_per_region(
                        regions,
                        stack_input,
                        target,
                        target_stage_override,
                        top_level_action,
                    )
                )

            stages.append(
                _codepipeline.CfnPipeline.StageDeclarationProperty(
                    name=stage_name,
                    actions=actions,
                )
            )
    return stages


def _generate_deployment_action_per_region(
    regions,
    stack_input,
    target,
    target_stage_override,
    top_level_action
):
    actions = []
    for region in regions:
        if "cloudformation" in target_stage_override:
            target_approval_mode = target.get("properties", {}).get(
                "change_set_approval", False
            )
            target_action_mode = target.get("properties", {}).get("action")
            action_mode = target_action_mode or top_level_action
            if action_mode:
                actions.extend([
                    adf_codepipeline.Action(
                        name=f"{target['name']}-{region}",
                        provider="CloudFormation",
                        category="Deploy",
                        region=region,
                        target=target,
                        action_mode=action_mode,
                        run_order=1,
                        map_params=stack_input["pipeline_input"],
                        action_name=f"{target['name']}-{region}",
                    ).config
                ])
                continue
            actions.extend(
                # ^^ Using extend without list,
                # as this generates multiple actions in a list
                adf_cloudformation.CloudFormation.generate_actions(
                    target,
                    region,
                    stack_input["pipeline_input"],
                    target_approval_mode,
                )
            )
        elif "codedeploy" in target_stage_override:
            actions.extend([
                adf_codepipeline.Action(
                    name=f"{target['name']}-{region}",
                    provider="CodeDeploy",
                    category="Deploy",
                    region=region,
                    target=target,
                    action_mode=top_level_action,
                    run_order=1,
                    map_params=stack_input["pipeline_input"],
                    action_name=f"{target['name']}-{region}",
                ).config
            ])
        elif "s3" in target_stage_override:
            actions.extend([
                adf_codepipeline.Action(
                    name=f"{target['name']}-{region}",
                    provider="S3",
                    category="Deploy",
                    region=region,
                    target=target,
                    action_mode=top_level_action,
                    run_order=1,
                    map_params=stack_input["pipeline_input"],
                    action_name=f"{target['name']}-{region}",
                ).config
            ])
        elif "lambda" in target_stage_override:
            actions.extend([
                adf_codepipeline.Action(
                    name=f"{target['name']}-{region}",
                    provider="Lambda",
                    category="Invoke",
                    region=region,
                    target=target,
                    action_mode=top_level_action,
                    run_order=1,
                    map_params=stack_input["pipeline_input"],
                    action_name=f"{target['name']}-{region}",
                ).config
            ])
        elif "service_catalog" in target_stage_override:
            actions.extend([
                adf_codepipeline.Action(
                    name=f"{target['name']}-{region}",
                    provider="ServiceCatalog",
                    category="Deploy",
                    region=region,
                    target=target,
                    action_mode=top_level_action,
                    run_order=1,
                    map_params=stack_input["pipeline_input"],
                    action_name=f"{target['name']}-{region}",
                ).config
            ])
    return actions
