import os
from logger import configure_logger
from aws_cdk import (
    aws_lambda as _lambda,
    aws_sns as _sns,
    aws_iam as _iam,
    core
)

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]

LOGGER = configure_logger(__name__)

class Notifications(core.Construct):
    def __init__(self, scope: core.Construct, id: str, map_params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)
        _slack_func = _lambda.Function.from_function_arn(
            self,
            'SlackNotificationLambda',
            'arn:aws:lambda:{0}:{1}:function:SendSlackNotification'.format(
                ADF_DEPLOYMENT_REGION,
                ADF_DEPLOYMENT_ACCOUNT_ID
            )
        )
        _topic = _sns.Topic(self, 'PipelineTopic')
        _statement = _iam.PolicyStatement(
            actions=["sns:Publish"],
            effect=_iam.Effect.ALLOW,
            principals=[
                _iam.ServicePrincipal(
                    'sns.amazonaws.com'
                ),
                _iam.ServicePrincipal(
                    'codecommit.amazonaws.com'
                ),
                _iam.ServicePrincipal(
                    'events.amazonaws.com'
                )
            ],
            resources=["*"]
        )
        _topic.add_to_resource_policy(_statement)
        _slack_func.add_permission(
            'slack_notification_sns_permissions',
            principal=_iam.ServicePrincipal('sns.amazonaws.com'),
            action='lambda:InvokeFunction',
            source_arn=_topic.topic_arn
        )
        _sub = _sns.Subscription(
            self,
            'SNSSubscription',
            topic=_topic,
            endpoint=map_params.get('notification_endpoint') if '@' in map_params.get('notification_endpoint') else _slack_func.function_arn,
            protocol=_sns.SubscriptionProtocol.EMAIL if '@' in map_params.get('notification_endpoint') else _sns.SubscriptionProtocol.LAMBDA
        )
        map_params['topic_arn'] = _topic.topic_arn



