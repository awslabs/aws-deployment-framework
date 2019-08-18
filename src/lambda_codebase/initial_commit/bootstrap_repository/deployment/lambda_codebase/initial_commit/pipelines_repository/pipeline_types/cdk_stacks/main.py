import os

from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_sns as _sns,
    aws_lambda as _lambda,
    core
)
from cdk_constructs.adf_helpers import Helpers
from cdk_constructs import adf_codepipeline
from cdk_constructs import adf_codebuild
from cdk_constructs import adf_cloudformation
from cdk_constructs import adf_events

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]
ADF_DEFAULT_SOURCE_ROLE = os.environ["ADF_DEFAULT_SOURCE_ROLE"]
ADF_DEFAULT_BUILD_ROLE = os.environ["ADF_DEFAULT_BUILD_ROLE"]
ADF_PROJECT_NAME = os.environ["ADF_PROJECT_NAME"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20

def _generate_actions(targets, region, map_params):
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
        _actions.append(
            adf_codepipeline.Action(
                name="{0}-{1}-execute".format(target['name'], region),
                provider="CloudFormation",
                category="Deploy",
                region=region,
                target=target,
                run_order=2,
                action_mode="CHANGE_SET_EXECUTE",
                map_params=map_params,
                action_name="{0}-{1}-execute".format(target['name'], region)
            ).config
        )
    return _actions


class PipelineStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, map_params: dict, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        _helpers = Helpers(self, 'adf_helpers')
        _source_name = map_params["type"]["source"]["name"].lower()
        _build_name = map_params["type"]["build"]["name"].lower()
        _stages = []
        if map_params.get('notification_endpoint'):
            _slack_func = _lambda.Function.from_function_arn(
                self,
                'SlackNotificationLambda',
                'arn:aws:lambda:{0}:{1}:function:SendSlackNotification'.format(
                    ADF_DEPLOYMENT_REGION,
                    ADF_DEPLOYMENT_ACCOUNT_ID
                )
            )
            _topic = _sns.Topic(self, 'PipelineTopic')
            _sub = _sns.Subscription(
                self, 
                'SNSSubscription',
                topic=_topic,
                endpoint=map_params.get('notification_endpoint') if '@' in map_params.get('notification_endpoint') else _slack_func.function_arn,
                protocol=_sns.SubscriptionProtocol.EMAIL if '@' in map_params.get('notification_endpoint') else _sns.SubscriptionProtocol.LAMBDA
            )
            map_params['topic_arn'] = _topic.topic_arn
        ssm_params = _helpers.fetch_required_ssm_params(map_params["regions"])
        if 'codecommit' in _source_name:
            _stages.append(
                _codepipeline.CfnPipeline.StageDeclarationProperty(
                    name="Source-{0}".format(map_params.get("type", {}).get("source", {}).get("account_id", ADF_DEPLOYMENT_ACCOUNT_ID)),
                    actions=[
                        adf_codepipeline.Action(
                            name="source",
                            provider="CodeCommit",
                            category="Source",
                            run_order=1,
                            map_params=map_params,
                            action_name="source"
                        ).config
                    ]
                )
            )
        elif 'github' in _source_name:
            pass
        elif 's3' in _source_name:
            pass

        if 'codebuild' in _build_name:
            adf_codebuild.CodeBuild(
                self,
                'CodeBuild',
                ssm_params[ADF_DEPLOYMENT_REGION]["modules"],
                ssm_params[ADF_DEPLOYMENT_REGION]["kms"]
            )
            _stages.append(
                _codepipeline.CfnPipeline.StageDeclarationProperty(
                    name="Build",
                    actions=[
                        adf_codepipeline.Action(
                            name="Build",
                            provider="CodeBuild",
                            category="Build",
                            run_order=1,
                            map_params=map_params,
                            action_name="build"
                        ).config
                    ]
                )
            )
        elif 'jenkins' in _build_name:
            pass

        for index, targets in enumerate(map_params.get('environments', {}).get('targets', [])):
            _actions = []
            top_level_deployment_type = map_params.get('type', {}).get('deploy', {}).get('name', {}) or 'cloudformation'
            top_level_action = map_params.get('type', {}).get('deploy', {}).get('action', {})
            for target in targets:
                if target.get('name') == 'approval':
                    _actions.extend([
                        adf_codepipeline.Action(
                            name="{0}-{1}".format(target['name'], region),
                            provider="Manual",
                            category="Approval",
                            region=region,
                            target=target,
                            action_mode=action_mode,
                            run_order=1,
                            map_params=map_params,
                            action_name="{0}-{1}".format(target['name'], region)
                        ).config
                    ])
                    continue
                regions = map_params.get('regions', target.get('regions'))
                for region in regions:
                    target_deployment_override = target.get('type', {}).get('deploy', {}).get('name', {}) or top_level_deployment_type
                    if 'cloudformation' in target_deployment_override:
                        action_mode = target.get('type', {}).get('deploy', {}).get('action', {}) or top_level_action
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
                                    map_params=map_params,
                                    action_name="{0}-{1}".format(target['name'], region)
                                ).config
                            ])
                            continue
                        _actions.extend(_generate_actions(target, region, map_params))
                    elif 'codedeploy' in target_deployment_override:
                        pass
                    elif 's3' in target_deployment_override:
                        pass
                    elif 'service_catalog' in target_deployment_override:
                        pass
            _name = 'approval' if targets[0]['name'].startswith('approval') else 'deployment'
            _stages.append(
                _codepipeline.CfnPipeline.StageDeclarationProperty(
                    name='{0}-stage-{1}'.format(_name, index + 1),
                    actions=_actions
                )
            )
        adf_codepipeline.Pipeline(self, 'CodePipeline', map_params, ssm_params, _stages)
