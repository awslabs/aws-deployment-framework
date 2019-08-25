import os
# from errors import InvalidProviderError
from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_sns as _sns,
    aws_lambda as _lambda,
    aws_secretsmanager as _secrets,
    core
)
from cdk_constructs import adf_events

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]
ADF_DEFAULT_SOURCE_ROLE = os.environ["ADF_DEFAULT_SOURCE_ROLE"]
ADF_DEFAULT_BUILD_ROLE = os.environ["ADF_DEFAULT_BUILD_ROLE"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_STACK_PREFIX = os.environ.get("ADF_STACK_PREFIX", "")
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
        self.region = kwargs.get('target', {}).get('region') or ADF_DEPLOYMENT_REGION
        self.account_id = self.map_params["type"]["source"].get("account_id")
        self.role_arn = self._generate_role_arn()
        self.notification_endpoint = self.target.get("params", {}).get("notification_endpoint") or self.map_params.get("params", {}).get("notification_endpoint")
        self.configuration = self._generate_configuration()
        self.config = self.generate()

    def _generate_role_arn(self):
        if self.map_params["type"]["build"].get("role"):
            if self.provider == 'CodeBuild' and self.category == 'Build':
                # CodePipeline would need access to assume this if you pass in a custom role
                return 'arn:aws:iam::{0}:role/{1}'.format(self.account_id, self.map_params["type"]["build"].get("role"))
        if self.map_params["type"]["deploy"].get("role"):
            if self.category == 'Deploy':
                # CodePipeline would need access to assume this if you pass in a custom role
                return 'arn:aws:iam::{0}:role/{1}'.format(self.account_id, self.map_params["type"]["deploy"]["role"])
        return None

    def _generate_configuration(self):
        if self.provider == "Manual" and self.category == "Approval":
            _config = {
                "CustomData": "Approval stage for {0}".format(self.map_params['name'])
            }
            if self.map_params.get('params', {}).get('notification_endpoint'):
                _config["NotificationArn"] = self.map_params['topic_arn']
            return _config
        if self.provider == "S3" and self.category == "Source":
            return {}
        if self.provider == "S3" and self.category == "Deploy":
            return {}
        if self.provider == "GitHub":
            return {
                "Owner": self.map_params.get('type', {}).get('source').get('owner', {}),
                "Repo": self.map_params.get('type', {}).get('source', {}).get('repository', {}) or self.map_params['name'],
                "Branch": self.map_params.get('branch', 'master'),
                "OAuthToken": core.SecretValue.secrets_manager(self.map_params['type']['source'].get('oauth_token_path'),
                        json_field=self.map_params['type']['source'].get('json_field')
                ),
                "PollForSourceChanges": False
            }
        if self.provider == "CloudFormation":
            return {
                "ActionMode": self.action_mode,
                "StackName": self.target.get('stack_name') or "{0}{1}".format(ADF_STACK_PREFIX, self.map_params['name']),
                "ChangeSetName": "{0}{1}".format(ADF_STACK_PREFIX, self.map_params['name']),
                "TemplatePath": "{0}-build::template.yml".format(self.map_params['name']),
                "TemplateConfiguration": "{0}-build::params/{1}_{2}.json".format(self.map_params['name'], self.target['name'], self.region),
                "Capabilities": "CAPABILITY_NAMED_IAM,CAPABILITY_AUTO_EXPAND",
                "RoleArn": "arn:aws:iam::{0}:role/adf-cloudformation-deployment-role".format(self.target['id']) if not self.role_arn else self.role_arn
            }
        if self.provider == "CodeBuild":
            return {
                "ProjectName": "adf-build-{0}".format(self.map_params['name'])
            }
        if self.provider == "CodeCommit":
            return {
                "BranchName": self.map_params.get('branch', 'master'),
                "RepositoryName": self.map_params.get('type', {}).get('source', {}).get('repository', {}) or self.map_params['name']
            }
        raise Exception("{0} is not a valid provider".format(self.provider))

    def _generate_codepipeline_access_role(self):
        if self.provider == "CodeCommit":
            return "arn:aws:iam::{0}:role/adf-codecommit-role".format(self.map_params['type']['source']['account_id'])
        if self.provider == "CodeBuild":
            return None
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
            "configuration":self.configuration,
            "name": self.action_name,
            "region":self.region or ADF_DEPLOYMENT_REGION,
            "run_order":self.run_order
        }
        if _role:
            action_props["role_arn"] = _role
        if self.category == 'Manual':
            del action_props['region']
        if self.category == 'Build':
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
        if self.category == 'Deploy':
            action_props["input_artifacts"] = [
                _codepipeline.CfnPipeline.InputArtifactProperty(
                    name="{0}-build".format(self.map_params['name'])
                )
            ]
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
        self.map_params = map_params
        self.ssm_params = ssm_params

        super().__init__(scope, id, **kwargs)
        [_codepipeline_role_arn, _code_build_role_arn, _send_slack_notification_lambda_arn] = Pipeline.import_required_arns()
        _pipeline_args = {
            "role_arn": _codepipeline_role_arn,
            "restart_execution_on_update": self.map_params.get('restart_execution_on_update', False),
            "name": "{0}{1}".format(ADF_STACK_PREFIX, map_params['name']),
            "stages": stages,
            "artifact_stores": self.generate_artifact_stores()
        }
        self.cfn = _codepipeline.CfnPipeline(
            self,
            'pipeline',
            **_pipeline_args
        )
        if map_params.get('topic_arn'):
            adf_events.Events(self, 'events', {
                "pipeline": self.cfn.ref,
                "topic_arn": map_params['topic_arn'],
                "name": map_params['name']
            })


    def generate_artifact_stores(self):
        output = []
        for region in self.map_params["regions"]:
            output.append(_codepipeline.CfnPipeline.ArtifactStoreMapProperty(
                artifact_store=_codepipeline.CfnPipeline.ArtifactStoreProperty(
                    location=self.ssm_params[region]["s3"],
                    type="S3",
                    encryption_key=_codepipeline.CfnPipeline.EncryptionKeyProperty(
                        id=self.ssm_params[region]["kms"],
                        type="KMS"
                    )
                ),
                region=region
            ))
        return output

    @staticmethod
    def import_required_arns():
        output = []
        for arn in Pipeline._import_arns:
            output.append(core.Fn.import_value(arn))
        return output