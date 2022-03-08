# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to Events Input
"""


import os
from aws_cdk import (
    aws_events as _events,
    aws_events_targets as _targets,
    aws_codepipeline as _codepipeline,
    aws_sns as _sns,
    core
)


ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20
ADF_PIPELINE_PREFIX = os.environ.get("ADF_PIPELINE_PREFIX", "")


class Events(core.Construct):
    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs):  # pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        # pylint: disable=no-value-for-parameter
        stack = core.Stack.of(self)
        _pipeline = _codepipeline.Pipeline.from_pipeline_arn(self, 'pipeline', params["pipeline"])
        _source_account = params.get('source', {}).get('account_id')
        _provider = params.get('source', {}).get('provider')
        _add_trigger_on_changes = (
            _provider == 'codecommit'
            and _source_account
            and params.get('source', {}).get('trigger_on_changes')
            and not params.get('source', {}).get('poll_for_changes')
        )

        name = params.get('name')
        account_id = params['source']['account_id']
        repo_name = params['source']['repo_name']

        if _add_trigger_on_changes:
            _event = _events.Rule(
                self,
                f'trigger_{name}',
                description=f'Triggers {name} on changes in source CodeCommit repository',
                event_pattern=_events.EventPattern(
                    resources=[
                        f'arn:{stack.partition}:codecommit:{ADF_DEPLOYMENT_REGION}:{account_id}:{repo_name}'
                    ],
                    source=["aws.codecommit"],
                    detail_type=[
                        'CodeCommit Repository State Change'
                    ],
                    detail={
                        "event": [
                            "referenceCreated",
                            "referenceUpdated"
                        ],
                        "referenceType": [
                            "branch"
                        ],
                        "referenceName": [
                            params['source']['branch']
                        ]
                    }
                )
            )
            _event.add_target(
                _targets.CodePipeline(
                    pipeline=_pipeline
                )
            )
        if params.get('topic_arn'):
            # pylint: disable=no-value-for-parameter
            _topic = _sns.Topic.from_topic_arn(self, 'topic_arn', params["topic_arn"])
            _event = _events.Rule(
                self,
                f'pipeline_state_{name}',
                description=f"{name} | Trigger notifications based on pipeline state changes",
                enabled=True,
                event_pattern=_events.EventPattern(
                    detail={
                        "state": [
                            "FAILED",
                            "STARTED",
                            "SUCCEEDED"
                        ],
                        "pipeline": [
                            f"{ADF_PIPELINE_PREFIX}{name}",
                        ]
                    },
                    detail_type=[
                        "CodePipeline Pipeline Execution State Change"
                    ],
                    source=["aws.codepipeline"]
                )
            )
            _event.add_target(
                _targets.SnsTopic(
                    topic=_topic,
                    message=_events.RuleTargetInput.from_text(
                        # Need to parse and get the pipeline: "$.detail.pipeline" state: "$.detail.state"
                        f"The pipeline {_events.EventField.from_path('$.detail.pipeline')} "
                        f"from account {_events.EventField.account} "
                        f"has {_events.EventField.from_path('$.detail.state')} "
                        f"at {_events.EventField.time}."
                    )
                )
            )
        if params.get('completion_trigger'):
            # There might be other types of completion triggers later, eg lambda..
            for index, pipeline in enumerate(params['completion_trigger'].get('pipelines', [])):
                _event = _events.Rule(
                    self,
                    f'completion_{pipeline}',
                    description="Triggers {pipeline} on completion of {params['pipeline']}",
                    enabled=True,
                    event_pattern=_events.EventPattern(
                        detail={
                            "state": [
                                "SUCCEEDED"
                            ],
                            "pipeline": [
                                f"{ADF_PIPELINE_PREFIX}{name}",
                            ]
                        },
                        detail_type=[
                            "CodePipeline Pipeline Execution State Change"
                        ],
                        source=["aws.codepipeline"]
                    )
                )
                # pylint: disable=no-value-for-parameter
                _completion_pipeline = _codepipeline.Pipeline.from_pipeline_arn(
                    self,
                    f'pipeline-{index}',
                    f'arn:{stack.partition}:codepipeline:'
                    f'{ADF_DEPLOYMENT_REGION}:{ADF_DEPLOYMENT_ACCOUNT_ID}:'
                    f'{ADF_PIPELINE_PREFIX}{pipeline}'
                )
                _event.add_target(
                    _targets.CodePipeline(
                        pipeline=_completion_pipeline
                    )
                )
        if params.get('schedule'):
            _event = _events.Rule(
                self,
                f'schedule_{params["name"]}',
                description=f"Triggers {params['name']} on a schedule of {params['schedule']}",
                enabled=True,
                # pylint: disable=no-value-for-parameter
                schedule=_events.Schedule.expression(params['schedule'])
            )
            _target_pipeline = _targets.CodePipeline(
                pipeline=_pipeline
            )
            _event.add_target(
                _target_pipeline
            )
