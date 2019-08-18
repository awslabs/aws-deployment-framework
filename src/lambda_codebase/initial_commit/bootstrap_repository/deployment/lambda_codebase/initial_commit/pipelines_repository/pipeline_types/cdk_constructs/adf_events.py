import os
from aws_cdk import (
    aws_events as _events,
    aws_events_targets as _targets,
    aws_sns as _sns,
    core
)

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]
ADF_DEFAULT_SOURCE_ROLE = os.environ["ADF_DEFAULT_SOURCE_ROLE"]
ADF_DEFAULT_BUILD_ROLE = os.environ["ADF_DEFAULT_BUILD_ROLE"]
ADF_PROJECT_NAME = os.environ["ADF_PROJECT_NAME"]
ADF_DEFAULT_BUILD_TIMEOUT = 20


class Events(core.Construct):
    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)
        _target = _targets.SnsTopic(
            topic=_sns.Topic.from_topic_arn(self, 'TopicArn', params["topic_arn"])
        )
        _event = _events.Rule(
            self,
            'Rule',
            description="Trigger notifications based on pipeline state changes",
            enabled=True,
            event_pattern=_events.EventPattern(
                source="aws.codepipeline",
                detail_type="CodePipeline Pipeline Execution State Change",
                detail={
                    "state": [
                        "FAILED",
                        "STARTED",
                        "SUCCEEDED"
                    ],
                    "pipeline": params["pipeline"]
                }
            ),
            targets=_target
        )
        # _event.add_target(
        #     target=_events.IRuleTarget.bind(
        #         rule=
        #     )
        # )

#         - Arn: !Ref PipelineSNSTopic
#           Id: !If [HasCustomRepository, !Sub "adf-pipeline-${ProjectName}", !Sub "adf-pipeline-${AWS::StackName}"]
# {% if "@" in notification_endpoint %}
#           InputTransformer:
#             InputTemplate: '"The pipeline <pipeline> from account <account> has <state> at <at>."'
#             InputPathsMap:
#               pipeline: "$.detail.pipeline"
#               state: "$.detail.state"
#               at: "$.time"
#               account: "$.account"
