# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json

from aws_cdk import (
    aws_codepipeline as _codepipeline,
    core
)

from errors import InvalidConfigError
from cdk_constructs import adf_events

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_STACK_PREFIX = os.environ.get("ADF_STACK_PREFIX", "")
ADF_PIPELINE_PREFIX = os.environ.get("ADF_PIPELINE_PREFIX", "")
ADF_DEFAULT_BUILD_TIMEOUT = 20

class Action:
    _version = "1"

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.target = kwargs.get('target', {})
        self.provider = kwargs.get('provider')
        self.category = kwargs.get('category')
        self.map_params = kwargs.get('map_params')
        self.owner = kwargs.get('owner') or 'AWS'
        self.run_order = kwargs.get('run_order')
        self.index = kwargs.get('index')
        self.action_name = kwargs.get('action_name')
        self.action_mode = kwargs.get('action_mode', '').upper()
        self.region = kwargs.get('region') or ADF_DEPLOYMENT_REGION
        self.account_id = self.map_params["type"]["source"].get("account_id")
        self.role_arn = self._generate_role_arn()
        self.notification_endpoint = self.map_params.get("topic_arn")
        self.configuration = self._generate_configuration()
        self._validate_configuration()
        self.config = self.generate()

    def _generate_role_arn(self):
        if self.target.get('type', {}).get('build', {}).get('role') or self.map_params["type"]["build"].get("role"):
            if self.provider == 'CodeBuild' and self.category == 'Build':
                # CodePipeline would need access to assume this if you pass in a custom role
                return 'arn:aws:iam::{0}:role/{1}'.format(self.account_id, self.map_params["type"]["build"].get("role"))
        if self.target.get('type', {}).get('deploy', {}).get('role') or self.map_params["type"]["deploy"].get("role"):
            if self.category == 'Deploy':
                return 'arn:aws:iam::{0}:role/{1}'.format(self.account_id, self.map_params["type"]["deploy"]["role"])
        return None

    def _validate_configuration(self):
        for _prop in self.configuration.items():
            try:
                assert _prop[1] is not None
                assert 'None' not in str(_prop[1])
            except AssertionError as _none_prop:
                raise InvalidConfigError("{0} has an invalid value of {1}".format(_prop[0], _prop[1])) from None

    def _generate_configuration(self):
        if self.provider == "Manual" and self.category == "Approval":
            _props = {
                "CustomData": self.target.get('type', {}).get('approval', {}).get('message') or "Approval stage for {0}".format(self.map_params['name'])
            }
            if self.notification_endpoint:
                _props["NotificationArn"] = self.notification_endpoint
            if self.target.get('type', {}).get('approval', {}).get('sns_topic_arn'):
                _props["NotificationArn"] = self.target.get('type', {}).get('approval', {}).get('sns_topic_arn')
            return _props
        if self.provider == "S3" and self.category == "Source":
            return {
                "S3Bucket": self.map_params.get('type', {}).get('source', {}).get('bucket_name'),
                "S3ObjectKey": self.map_params.get('type', {}).get('source', {}).get('object_key')
            }
        if self.provider == "S3" and self.category == "Deploy":
            return {
                "BucketName": self.map_params.get('type', {}).get('deploy', {}).get('bucket_name') or self.target.get('type', {}).get('deploy', {}).get('bucket_name'),
                "Extract": self.map_params.get('type', {}).get('deploy', {}).get('extract') or self.target.get('type', {}).get('deploy', {}).get('extract', False),
                "ObjectKey": self.map_params.get('type', {}).get('deploy', {}).get('object_key') or self.target.get('type', {}).get('deploy', {}).get('object_key')
            }
        if self.provider == "GitHub":
            return {
                "Owner": self.map_params.get('type', {}).get('source').get('owner', {}),
                "Repo": self.map_params.get('type', {}).get('source', {}).get('repository', {}) or self.map_params['name'],
                "Branch": self.map_params.get('type', {}).get('source', {}).get('branch', {}) or 'master',
                "OAuthToken": core.SecretValue.secrets_manager(
                    self.map_params['type']['source'].get('oauth_token_path'),
                    json_field=self.map_params['type']['source'].get('json_field')
                ),
                "PollForSourceChanges": False
            }
        if self.provider == "Lambda":
            return {
                "FunctionName": self.map_params.get('type', {}).get('invoke', {}).get('function_name', '') or self.target.get('type', {}).get('invoke', {}).get('function_name', ''),
                "UserParameters": str(self.map_params.get('type', {}).get('invoke', {}).get('input', '') or self.target.get('type', {}).get('invoke', {}).get('input', ''))
            }
        if self.provider == "CloudFormation":
            _props = {
                "ActionMode": self.action_mode,
                "StackName": self.target.get('type', {}).get('deploy', {}).get('stack_name') or "{0}{1}".format(ADF_STACK_PREFIX, self.map_params['name']),
                "ChangeSetName": "{0}{1}".format(ADF_STACK_PREFIX, self.map_params['name']),
                "TemplatePath": self.target.get('type', {}).get('deploy', {}).get('template_filename') or self.map_params.get('type', {}).get('deploy', {}).get('template_filename') or "{0}-build::template.yml".format(self.map_params['name']),
                "TemplateConfiguration": "{0}-build::params/{1}_{2}.json".format(self.map_params['name'], self.target['name'], self.region),
                "Capabilities": "CAPABILITY_NAMED_IAM,CAPABILITY_AUTO_EXPAND",
                "RoleArn": "arn:aws:iam::{0}:role/adf-cloudformation-deployment-role".format(self.target['id']) if not self.role_arn else self.role_arn
            }
            if self.target.get('type', {}).get('deploy', {}).get('outputs'):
                _props['OutputFileName'] = '{0}.json'.format(self.target['type']['deploy']['outputs'])
            if self.target.get('type', {}).get('deploy', {}).get('param_overrides'):
                _overrides = {}
                for override in self.target.get('type', {}).get('deploy', {}).get('param_overrides', []):
                    _overrides["{0}".format(override['param'])] = {"Fn::GetParam": ["{0}".format(override['inputs']), "{0}.json".format(override['inputs']), "{0}".format(override['key_name'])]}
                _props['ParameterOverrides'] = json.dumps(_overrides)
            return _props
        if self.provider == "Jenkins":
            return {
                "ProjectName": self.map_params['type']['build'].get('project_name', self.map_params['name']), # Enter the name of the project you created in the Jenkins plugin
                "ServerURL": self.map_params['type']['build']['server_url'], # Server URL
                "ProviderName": self.map_params['type']['build']['provider_name'] # Enter the provider name you configured in the Jenkins plugin
            }
        if self.provider == "CodeBuild":
            return {
                "ProjectName": "adf-build-{0}".format(self.map_params['name'])
            }
        if self.provider == "ServiceCatalog":
            return {
                "ConfigurationFilePath": self.target.get('type', {}).get('deploy', {}).get('configuration_file_path') or "params/{0}_{1}.json".format(self.target['name'], self.region),
                "ProductId": self.target.get('type', {}).get('deploy', {}).get('product_id') or self.map_params['type']['deploy'].get('product_id') # product_id is required for Service Catalog, meaning the product must already exist.
            }
        if self.provider == "CodeDeploy":
            return {
                "ApplicationName": self.map_params.get('type', {}).get('deploy', {}).get('application_name', {}) or self.target.get('type', {}).get('deploy', {}).get('application_name'),
                "DeploymentGroupName": self.map_params.get('type', {}).get('deploy', {}).get('deployment_group_name', {}) or self.target.get('type', {}).get('deploy', {}).get('deployment_group_name')
            }
        if self.provider == "CodeCommit":
            return {
                "BranchName": self.map_params['type']['source'].get('branch', 'master'),
                "RepositoryName": self.map_params['type']['source'].get('repository', {}) or self.map_params['name'],
                "PollForSourceChanges": self.map_params['type']['source'].get('poll_for_changes', False)
            }
        raise Exception("{0} is not a valid provider".format(self.provider))

    def _generate_codepipeline_access_role(self):
        if self.provider == "CodeCommit":
            return "arn:aws:iam::{0}:role/adf-codecommit-role".format(self.map_params['type']['source']['account_id'])
        if self.provider == "CodeBuild":
            return None
        if self.provider == "S3" and self.category == "Source":
            # This could be changed to use a new role that is bootstrapped, ideally we rename adf-cloudformation-role to a generic deployment role name
            return "arn:aws:iam::{0}:role/adf-codecommit-role".format(self.map_params['type']['source']['account_id'])
        if self.provider == "S3" and self.category == "Deploy":
            # This could be changed to use a new role that is bootstrapped, ideally we rename adf-cloudformation-role to a generic deployment role name
            return "arn:aws:iam::{0}:role/adf-cloudformation-role".format(self.map_params['type']['source']['account_id'])
        if self.provider == "ServiceCatalog":
            # This could be changed to use a new role that is bootstrapped, ideally we rename adf-cloudformation-role to a generic deployment role name
            return "arn:aws:iam::{0}:role/adf-cloudformation-role".format(self.target['id'])
        if self.provider == "CodeDeploy":
            # This could be changed to use a new role that is bootstrapped, ideally we rename adf-cloudformation-role to a generic deployment role name
            return "arn:aws:iam::{0}:role/adf-cloudformation-role".format(self.target['id'])
        if self.provider == "CloudFormation":
            return "arn:aws:iam::{0}:role/adf-cloudformation-role".format(self.target['id'])
        if self.provider == "Manual":
            return None

    def generate(self):
        _role = self._generate_codepipeline_access_role()
        action_props = {
            "action_type_id":_codepipeline.CfnPipeline.ActionTypeIdProperty(
                version=Action._version,
                owner=self.owner,
                provider=self.provider,
                category=self.category
            ),
            "configuration": self.configuration,
            "name": self.action_name,
            "region": self.region or ADF_DEPLOYMENT_REGION,
            "run_order": self.run_order
        }
        if _role:
            action_props["role_arn"] = _role
        if self.category == 'Manual':
            del action_props['region']
        if self.category == 'Build' and not self.target:
            action_props["input_artifacts"] = [
                _codepipeline.CfnPipeline.InputArtifactProperty(
                    name="output-source"
                )
            ]
            action_props["output_artifacts"] = [
                _codepipeline.CfnPipeline.OutputArtifactProperty(
                    name="{0}-build".format(self.map_params['name'])
                )
            ]
        if self.category == 'Build' and self.target:
            action_props["input_artifacts"] = [
                _codepipeline.CfnPipeline.InputArtifactProperty(
                    name="{0}-build".format(self.map_params['name'])
                )
            ]
        if self.category == 'Deploy':
            action_props["input_artifacts"] = [
                _codepipeline.CfnPipeline.InputArtifactProperty(
                    name="{0}-build".format(self.map_params['name'])
                )
            ]
            if self.provider == "CloudFormation" and self.target.get('type', {}).get('deploy', {}).get('outputs') and self.action_mode != 'CHANGE_SET_REPLACE':
                action_props["output_artifacts"] = [
                    _codepipeline.CfnPipeline.OutputArtifactProperty(
                        name=self.target.get('type', {}).get('deploy', {}).get('outputs')
                    )
                ]
            if not self.map_params.get('type', {}).get('build', {}).get('enabled', True):
                action_props["input_artifacts"] = [
                    _codepipeline.CfnPipeline.OutputArtifactProperty(
                        name="output-source"
                    )
                ]
            for override in self.target.get('type', {}).get('deploy', {}).get('param_overrides', []):
                if self.provider == "CloudFormation" and override.get('inputs') and self.action_mode != "CHANGE_SET_EXECUTE":
                    action_props["input_artifacts"].append(
                        _codepipeline.CfnPipeline.InputArtifactProperty(
                            name=override.get('inputs')
                        )
                    )
        if self.category == 'Source':
            action_props["output_artifacts"] = [
                _codepipeline.CfnPipeline.OutputArtifactProperty(
                    name="output-source"
                )
            ]
        return _codepipeline.CfnPipeline.ActionDeclarationProperty(
            **action_props
        )

class Pipeline(core.Construct):
    _import_arns = [
        'CodePipelineRoleArn',
        'CodeBuildRoleArn',
        'SendSlackNotificationLambdaArn'
    ]

    def __init__(self, scope: core.Construct, id: str, map_params: dict, ssm_params: dict, stages, **kwargs):
        super().__init__(scope, id, **kwargs)
        [_codepipeline_role_arn, _code_build_role_arn, _send_slack_notification_lambda_arn] = Pipeline.import_required_arns()
        _pipeline_args = {
            "role_arn": _codepipeline_role_arn,
            "restart_execution_on_update": map_params.get('restart_execution_on_update', False),
            "name": "{0}{1}".format(ADF_PIPELINE_PREFIX, map_params['name']),
            "stages": stages,
            "artifact_stores": Pipeline.generate_artifact_stores(map_params, ssm_params)
        }
        self.cfn = _codepipeline.CfnPipeline(
            self,
            'pipeline',
            **_pipeline_args
        )
        adf_events.Events(self, 'events', {
            "pipeline": 'arn:aws:codepipeline:{0}:{1}:{2}'.format(ADF_DEPLOYMENT_REGION, ADF_DEPLOYMENT_ACCOUNT_ID, "{0}{1}".format(os.environ.get("ADF_PIPELINE_PREFIX"), map_params['name'])),
            "topic_arn": map_params.get('topic_arn'),
            "name": map_params['name'],
            "completion_trigger": map_params.get('completion_trigger'),
            "schedule": map_params.get('schedule'),
            "source": {
                "account_id": map_params.get('type', {}).get('source', {}).get('account_id'),
                "repo_name": map_params.get('type', {}).get('source', {}).get('repository') or map_params['name']
            }
        })

    @staticmethod
    def generate_artifact_stores(map_params, ssm_params):
        output = []
        for region in map_params["regions"]:
            output.append(_codepipeline.CfnPipeline.ArtifactStoreMapProperty(
                artifact_store=_codepipeline.CfnPipeline.ArtifactStoreProperty(
                    location=ssm_params[region]["s3"],
                    type="S3",
                    encryption_key=_codepipeline.CfnPipeline.EncryptionKeyProperty(
                        id=ssm_params[region]["kms"],
                        type="KMS"
                    )
                ),
                region=region
            ))
        return output

    @staticmethod
    def import_required_arns():
        _output = []
        for arn in Pipeline._import_arns:
            _output.append(core.Fn.import_value(arn))
        return _output