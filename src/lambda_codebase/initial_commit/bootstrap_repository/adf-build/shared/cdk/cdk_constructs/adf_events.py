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
    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs): #pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        # pylint: disable=no-value-for-parameter
        _pipeline = _codepipeline.Pipeline.from_pipeline_arn(self, 'pipeline', params["pipeline"])
        _source_account = params.get('source', {}).get('account_id')
        _provider = params.get('source', {}).get('provider')
        if _source_account and _provider == 'codecommit':
            _event = _events.Rule(
                self,
                'trigger_{0}'.format(params["name"]),
                description="Triggers {0} on changes in source CodeCommit repository".format(params["name"]),
                event_pattern=_events.EventPattern(
                    resources=[
                        "arn:aws:codecommit:{0}:{1}:{2}".format(ADF_DEPLOYMENT_REGION, params['source']['account_id'], params['source']['repo_name'])
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
                'pipeline_state_{0}'.format(params["name"]),
                description="{0} | Trigger notifications based on pipeline state changes".format(params["name"]),
                enabled=True,
                event_pattern=_events.EventPattern(
                    detail={
                        "state": [
                            "FAILED",
                            "STARTED",
                            "SUCCEEDED"
                        ],
                        "pipeline": [
                            "{0}{1}".format(ADF_PIPELINE_PREFIX, params["name"])
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
                        "The pipeline {0} from account {1} has {2} at {3}.".format(
                            _events.EventField.from_path('$.detail.pipeline'), # Need to parse and get the pipeline: "$.detail.pipeline" state: "$.detail.state"
                            _events.EventField.account,
                            _events.EventField.from_path('$.detail.state'),
                            _events.EventField.time
                        )
                    )
                )
            )
        if params.get('completion_trigger'):
            # There might be other types of completion triggers later, eg lambda..
            for index, pipeline in enumerate(params['completion_trigger'].get('pipelines', [])):
                _event = _events.Rule(
                    self,
                    'completion_{0}'.format(pipeline),
                    description="Triggers {0} on completion of {1}".format(pipeline, params['pipeline']),
                    enabled=True,
                    event_pattern=_events.EventPattern(
                        detail={
                            "state": [
                                "SUCCEEDED"
                            ],
                            "pipeline": [
                                "{0}{1}".format(ADF_PIPELINE_PREFIX, params["name"])
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
                    'pipeline-{0}'.format(index),
                    "arn:aws:codepipeline:{0}:{1}:{2}".format(ADF_DEPLOYMENT_REGION, ADF_DEPLOYMENT_ACCOUNT_ID, "{0}{1}".format(
                        ADF_PIPELINE_PREFIX,
                        pipeline
                    )))
                _event.add_target(
                    _targets.CodePipeline(
                        pipeline=_completion_pipeline
                    )
                )
        if params.get('schedule'):
            _event = _events.Rule(
                self,
                'schedule_{0}'.format(params['name']),
                description="Triggers {0} on a schedule of {1}".format(params['name'], params['schedule']),
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
