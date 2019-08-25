import os
from aws_cdk import (
    aws_events as _events,
    aws_events_targets as _targets,
    aws_codepipeline as _codepipeline,
    aws_sns as _sns,
    core
)

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]
ADF_DEFAULT_SOURCE_ROLE = os.environ["ADF_DEFAULT_SOURCE_ROLE"]
ADF_DEFAULT_BUILD_ROLE = os.environ["ADF_DEFAULT_BUILD_ROLE"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20


class Events(core.Construct):
    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)
        _topic = _sns.Topic.from_topic_arn(self, 'topic_arn', params["topic_arn"])
        _pipeline = _codepipeline.Pipeline.from_pipeline_arn(self, 'pipeline', params["pipeline"])
        _on_state_change = _pipeline.on_state_change(
            id='pipeline_state_change_event',
            description="{0} | Trigger notifications based on pipeline state changes".format(params["name"]),
            event_pattern=_events.EventPattern(
                resources=[
                    "arn:aws:codepipeline:{0}:{1}:{2}".format(ADF_DEPLOYMENT_REGION, ADF_DEPLOYMENT_ACCOUNT_ID, params["pipeline"])
                ],
                account=[ADF_DEPLOYMENT_ACCOUNT_ID],
                detail={
                    "state": [
                        "FAILED",
                        "STARTED",
                        "SUCCEEDED"
                    ],
                    "pipeline": [
                        params["pipeline"]
                    ]
                }
            )
        )
        _on_state_change.add_target(
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
            for pipeline in params['completion_trigger'].get('pipelines', []):
                _event = _events.Rule(
                    self,
                    'CompletionRule',
                    description="Triggers {0} on a Completion".format(pipeline),
                    enabled=True,
                    schedule=params['schedule']
                )
                _target_pipeline = _targets.CodePipeline(
                    pipeline="arn:aws:codepipeline:${0}:${1}:${2}".format(
                        ADF_DEPLOYMENT_REGION,
                        ADF_DEPLOYMENT_ACCOUNT_ID,
                        pipeline
                    )
                )
                _event.add_target(
                    _target_pipeline
                )
        if params.get('schedule'):
            _event = _events.Rule(
                self,
                'ScheduleRule',
                description="Triggers {0} on a Schedule".format(params['name']),
                enabled=True,
                schedule=params['schedule']
            )
            _target_pipeline = _targets.CodePipeline(
                pipeline="arn:aws:codepipeline:${0}:${1}:${2}".format(
                    ADF_DEPLOYMENT_REGION,
                    ADF_DEPLOYMENT_ACCOUNT_ID,
                    params['name']
                )
            )
            _event.add_target(
                _target_pipeline
            )
