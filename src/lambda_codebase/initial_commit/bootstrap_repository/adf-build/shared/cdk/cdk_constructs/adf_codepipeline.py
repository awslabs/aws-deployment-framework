# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to CodePipeline Action Input
"""

import os
import json

from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_events as _eventbridge,
    aws_events_targets as _eventbridge_targets,
    SecretValue,
    Fn,
)
from constructs import Construct

from cdk_constructs import adf_events
from logger import configure_logger

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_STACK_PREFIX = os.environ.get("ADF_STACK_PREFIX", "")
ADF_PIPELINE_PREFIX = os.environ.get("ADF_PIPELINE_PREFIX", "")
ADF_DEFAULT_BUILD_TIMEOUT = 20
ADF_DEFAULT_SCM_FALLBACK_BRANCH = 'master'


LOGGER = configure_logger(__name__)


def get_partition(region_name: str) -> str:
    """Given the region, this function will return the appropriate partition.

    :param region_name: The name of the region (us-east-1, us-gov-west-1)
    :return: Returns the partition name as a string.
    """

    if region_name.startswith('us-gov'):
        return 'aws-us-gov'

    return 'aws'


ADF_DEPLOYMENT_PARTITION = get_partition(ADF_DEPLOYMENT_REGION)


class Action:
    _version = "1"

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.target = kwargs.get('target', {})
        self.provider = kwargs.get('provider')
        self.category = kwargs.get('category')
        self.map_params = kwargs.get('map_params')
        self.project_name = kwargs.get('project_name')
        self.owner = kwargs.get('owner') or 'AWS'
        self.run_order = kwargs.get('run_order')
        self.index = kwargs.get('index')
        self.action_name = kwargs.get('action_name')
        self.action_mode = kwargs.get('action_mode', '').upper()
        self.region = kwargs.get('region') or ADF_DEPLOYMENT_REGION
        self.account_id = (
            self.map_params["default_providers"]["source"]
            .get('properties', {})
            .get("account_id")
        )
        self.role_arn = self._generate_role_arn()
        self.notification_endpoint = self.map_params.get("topic_arn")
        self.default_scm_branch = self.map_params.get(
            "default_scm_branch",
            ADF_DEFAULT_SCM_FALLBACK_BRANCH,
        )
        self.configuration = self._generate_configuration()
        self.config = self.generate()

    def _generate_role_arn(self):
        if self.category not in ['Build', 'Deploy']:
            return None
        default_provider = (
            self.map_params['default_providers'][self.category.lower()]
        )
        specific_role = (
            self.target
            .get('properties', {})
            .get('role', default_provider.get('properties', {}).get('role'))
        )
        if specific_role:
            account_id = (
                self.account_id
                if self.provider == 'CodeBuild'
                else self.target['id']
            )
            return (
                f'arn:{ADF_DEPLOYMENT_PARTITION}:iam::{account_id}:'
                f'role/{specific_role}'
            )
        return None

    # pylint: disable=R0912, R0911, R0915
    def _generate_configuration(self):
        if self.provider == "Manual" and self.category == "Approval":
            props = {
                "CustomData": (
                    self.target
                    .get('properties', {})
                    .get(
                        'message',
                        f"Approval stage for {self.map_params['name']}",
                    )
                ),
            }
            if self.notification_endpoint:
                props["NotificationArn"] = self.notification_endpoint
            if self.target.get('properties', {}).get('sns_topic_arn'):
                props["NotificationArn"] = (
                    self.target
                    .get('properties', {})
                    .get('sns_topic_arn')
                )
            return props
        if self.provider == "S3" and self.category == "Source":
            return {
                "S3Bucket": (
                    self.map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('bucket_name')
                ),
                "S3ObjectKey": (
                    self.map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('object_key')
                ),
                "PollForSourceChanges": (
                    self.map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('trigger_on_changes', True)
                ),
            }
        if self.provider == "S3" and self.category == "Deploy":
            return {
                "BucketName": (
                    self.target
                    .get('properties', {})
                    .get('bucket_name', (
                        # Fallback to default provider deploy if not set
                        # in the target
                        self.map_params
                        .get('default_providers', {})
                        .get('deploy', {})
                        .get('properties', {})
                        .get('bucket_name')
                    ))
                ),
                "Extract": (
                    self.target
                    .get('properties', {})
                    .get('extract', (
                        self.map_params
                        .get('default_providers', {})
                        .get('deploy', {})
                        .get('properties', {})
                        .get('extract', False)
                    ))
                ),
                "ObjectKey": (
                    self.target
                    .get('properties', {})
                    .get('object_key', (
                        self.map_params
                        .get('default_providers', {})
                        .get('deploy', {})
                        .get('properties', {})
                        .get('object_key')
                    ))
                ),
            }
        if self.provider == "CodeStarSourceConnection":
            default_source_props = (
                self.map_params
                .get('default_providers', {})
                .get('source', {})
                .get('properties', {})
            )
            owner = default_source_props.get('owner')
            repo = (
                default_source_props
                .get('repository', self.map_params['name'])
            )
            if not default_source_props.get('codestar_connection_arn'):
                raise Exception(
                    "The CodeStar Connection Arn could not be resolved for "
                    f"the {self.map_params['name']} pipeline. Please check "
                    "whether the codestar_connection_path is setup correctly "
                    "and validate that the Parameter it points to is properly "
                    "configured in SSM Parameter Store."
                )
            props = {
                "ConnectionArn": default_source_props.get(
                    'codestar_connection_arn',
                ),
                "FullRepositoryId": f"{owner}/{repo}",
                "BranchName": default_source_props.get(
                    'branch',
                    self.default_scm_branch,
                )
            }
            output_artifact_format = default_source_props.get(
                'output_artifact_format',
            )
            if output_artifact_format:
                props["OutputArtifactFormat"] = output_artifact_format
            return props
        if self.provider == "GitHub":
            return {
                "Owner": (
                    self.map_params
                    .get('default_providers', {})
                    .get('source')
                    .get('properties', {})
                    .get('owner', '')
                ),
                "Repo": (
                    self.map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('repository', self.map_params['name'])
                ),
                "Branch": (
                    self.map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('branch', self.default_scm_branch)
                ),
                # pylint: disable=no-value-for-parameter
                "OAuthToken": SecretValue.secrets_manager(
                    (
                        self.map_params['default_providers']['source']
                        .get('properties', {})
                        .get('oauth_token_path')
                    ),
                    json_field=(
                        self.map_params['default_providers']['source']
                        .get('properties', {})
                        .get('json_field')
                    ),
                ),
                "PollForSourceChanges": False
            }
        if self.provider == "Lambda":
            return {
                "FunctionName": (
                    self.target
                    .get('properties', {})
                    .get('function_name', (
                        # Fallback to default function name if not set
                        self.map_params
                        .get('default_providers', {})
                        .get('deploy', {})
                        .get('properties', {})
                        .get('function_name', '')
                    ))
                ),
                "UserParameters": str(
                    self.target.get('properties', {})
                    .get('input', (
                        self.map_params.get('default_providers', {})
                        .get('deploy', {})
                        .get('properties', {})
                        .get('input', '')
                    ))
                ),
            }
        if self.provider == "CloudFormation":
            path_prefix = (
                self.target
                .get('properties', {})
                .get('root_dir', (
                    self.map_params
                    .get('default_providers', {})
                    .get('deploy', {})
                    .get('properties', {})
                    .get('root_dir', '')
                ))
            )
            if path_prefix and not path_prefix.endswith('/'):
                path_prefix = f"{path_prefix}/"
            input_artifact = f"{self.map_params['name']}-build"
            param_filename = (
                self.target
                .get('properties', {})
                .get('param_filename', (
                    # If target stack name is not set, fallback to default
                    self.map_params
                    .get('default_providers', {})
                    .get('deploy', {})
                    .get('properties', {})
                    .get(
                        'param_filename',
                        # If the default is not set, fallback to
                        # ADF default
                        f"{self.target['name']}_{self.region}.json",
                    )
                ))
            )
            props = {
                "ActionMode": self.action_mode,
                "StackName": (
                    self.target
                    .get('properties', {})
                    .get('stack_name', (
                        # If target stack name is not set, fallback to default
                        self.map_params
                        .get('default_providers', {})
                        .get('deploy', {})
                        .get('properties', {})
                        .get(
                            'stack_name',
                            # If the default is not set, fallback to
                            # ADF default
                            f"{ADF_STACK_PREFIX}{self.map_params['name']}",
                        )
                    ))
                ),
                "ChangeSetName": (
                    f"{ADF_STACK_PREFIX}{self.map_params['name']}"
                ),
                "TemplateConfiguration": (
                    f"{input_artifact}::{path_prefix}params/{param_filename}"
                ),
                "Capabilities": "CAPABILITY_NAMED_IAM,CAPABILITY_AUTO_EXPAND",
                "RoleArn": self.role_arn if self.role_arn else (
                    f"arn:{ADF_DEPLOYMENT_PARTITION}:iam::{self.target['id']}:"
                    f"role/adf-cloudformation-deployment-role"
                )
            }
            contains_transform = (
                self.map_params
                .get('default_providers', {})
                .get('build', {})
                .get('properties', {})
                .get('environment_variables', {})
                .get('CONTAINS_TRANSFORM')
            )
            template_filename = (
                self.target
                .get('properties', {})
                .get('template_filename', (
                    self.map_params
                    .get('default_providers', {})
                    .get('deploy', {})
                    .get('properties', {})
                    .get(
                        'template_filename',
                        (
                            f"template_{self.region}.yml"
                            if contains_transform
                            else "template.yml"
                        ),
                    )
                ))
            )
            props["TemplatePath"] = (
                f"{input_artifact}::{path_prefix}{template_filename}"
            )
            if self.target.get('properties', {}).get('outputs'):
                props['OutputFileName'] = (
                    f"{path_prefix}{self.target['properties']['outputs']}.json"
                )
            if self.target.get('properties', {}).get('param_overrides'):
                overrides = {}
                for override in (
                    self.target
                    .get('properties', {})
                    .get('param_overrides', [])
                ):
                    overrides[override['param']] = {
                        "Fn::GetParam": [
                            override['inputs'],
                            f"{override['inputs']}.json",
                            override['key_name'],
                        ],
                    }
                props['ParameterOverrides'] = json.dumps(overrides)
            return props
        if self.provider == "Jenkins":
            return {
                "ProjectName": (
                    # The name of the project you created in the Jenkins plugin
                    self.map_params['default_providers']['build']
                    .get('properties', {})
                    .get('project_name', self.map_params['name'])
                ),
                "ServerURL": (
                    self.map_params['default_providers']['build']
                    .get('properties', {})
                    .get('server_url')
                ),
                "ProviderName": (
                    # The provider name you configured in the Jenkins plugin
                    self.map_params['default_providers']['build']
                    .get('properties', {})
                    .get('provider_name')
                ),
            }
        if self.provider == "CodeBuild":
            return {
                "ProjectName": (
                    self.project_name or f"adf-build-{self.map_params['name']}"
                )
            }
        if self.provider == "ServiceCatalog":
            return {
                "ConfigurationFilePath": (
                    (
                        self.target
                        .get('properties', {})
                        .get(
                            'configuration_file_path',
                            f"params/{self.target['name']}_{self.region}.json",
                        )
                    )
                ),
                "ProductId": (
                    # The product_id is required for Service Catalog,
                    # meaning the product must already exist.
                    (
                        self.target
                        .get('properties', {})
                        .get('product_id', (
                            self.map_params['default_providers']['deploy']
                            .get('properties', {})
                            .get('product_id')
                        ))
                    )
                )
            }
        if self.provider == "CodeDeploy":
            return {
                "ApplicationName": (
                    self.target
                    .get('properties', {})
                    .get('application_name', (
                        self.map_params
                        .get('default_providers', {})
                        .get('deploy', {})
                        .get('properties', {})
                        .get('application_name', '')
                    ))
                ),
                "DeploymentGroupName": (
                    self.target
                    .get('properties', {})
                    .get('deployment_group_name', (
                        self.map_params
                        .get('default_providers', {})
                        .get('deploy', {})
                        .get('properties', {})
                        .get('deployment_group_name', '')
                    ))
                ),
            }
        if self.provider == "CodeCommit":
            props = {
                "BranchName": (
                    self.map_params['default_providers']['source']
                    .get('properties', {})
                    .get('branch', self.default_scm_branch)
                ),
                "RepositoryName": (
                    self.map_params['default_providers']['source']
                    .get('properties', {})
                    .get('repository', self.map_params['name'])
                ),
                "PollForSourceChanges": (
                    (
                        self.map_params['default_providers']['source']
                        .get('properties', {})
                        .get('trigger_on_changes', True)
                    ) and (
                        self.map_params['default_providers']['source']
                        .get('properties', {})
                        .get('poll_for_changes', False)
                    )
                ),
            }
            output_artifact_format = (
                self.map_params['default_providers']['source']
                .get('properties', {})
                .get('output_artifact_format')
            )
            if output_artifact_format:
                props["OutputArtifactFormat"] = output_artifact_format
            return props
        raise Exception(f"{self.provider} is not a valid provider")

    def _generate_codepipeline_access_role(self):  # pylint: disable=R0911
        account_id = (
            self.map_params['default_providers']['source']
            .get('properties', {})
            .get('account_id', '')
        )

        if self.provider == "GitHub":
            return None
        if self.provider == "CodeStarSourceConnection":
            return None
        if self.provider == "CodeBuild":
            return None
        if self.provider == "CodeCommit":
            return (
                f"arn:{ADF_DEPLOYMENT_PARTITION}:iam::{account_id}:"
                "role/adf-codecommit-role"
            )
        if self.provider == "S3" and self.category == "Source":
            return (
                f"arn:{ADF_DEPLOYMENT_PARTITION}:iam::{account_id}:"
                "role/adf-codecommit-role"
            )
        if self.provider == "S3" and self.category == "Deploy":
            # This could be changed to use a new role that is bootstrapped,
            # ideally we rename adf-cloudformation-role to a
            # generic deployment role name
            return (
                f"arn:{ADF_DEPLOYMENT_PARTITION}:iam::{self.target['id']}:"
                "role/adf-cloudformation-role"
            )
        if self.provider == "ServiceCatalog":
            # This could be changed to use a new role that is bootstrapped,
            # ideally we rename adf-cloudformation-role to a
            # generic deployment role name
            return (
                f"arn:{ADF_DEPLOYMENT_PARTITION}:iam::{self.target['id']}:"
                "role/adf-cloudformation-role"
            )
        if self.provider == "CodeDeploy":
            # This could be changed to use a new role that is bootstrapped,
            # ideally we rename adf-cloudformation-role to a
            # generic deployment role name
            return (
                f"arn:{ADF_DEPLOYMENT_PARTITION}:iam::{self.target['id']}:"
                "role/adf-cloudformation-role"
            )
        if self.provider == "Lambda":
            # This could be changed to use a new role that is bootstrapped,
            # ideally we rename adf-cloudformation-role to a
            # generic deployment role name
            return None
        if self.provider == "CloudFormation":
            return (
                f"arn:{ADF_DEPLOYMENT_PARTITION}:iam::{self.target['id']}:"
                "role/adf-cloudformation-role"
            )
        if self.provider == "Manual":
            return None
        raise Exception(f'Invalid Provider {self.provider}')

    def generate(self):
        pipeline_role = self._generate_codepipeline_access_role()
        action_props = {
            "action_type_id": _codepipeline.CfnPipeline.ActionTypeIdProperty(
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
        input_artifacts = self._get_input_artifacts()
        if input_artifacts:
            action_props["input_artifacts"] = input_artifacts
        output_artifacts = self._get_output_artifacts()
        if output_artifacts:
            action_props["output_artifacts"] = output_artifacts
        if pipeline_role:
            action_props["role_arn"] = pipeline_role
        if self.category == 'Manual':
            del action_props['region']

        return _codepipeline.CfnPipeline.ActionDeclarationProperty(
            **action_props
        )

    def _get_base_input_artifact_name(self):
        """
        Determine the name for the input artifact for this action.

        Returns:
            str: The output artifact name as a string
        """
        use_output_source = (
            not self.target
            or not (
                self.map_params
                .get('default_providers', {})
                .get('build', {})
                .get('enabled', True)
            )
        )
        if use_output_source:
            return "output-source"
        return f"{self.map_params['name']}-build"

    def _get_input_artifacts(self):
        """
        Generate the list of input artifacts that are required for this action

        Returns:
            list<CfnPipeline.InputArtifactProperty>: The Input Artifacts
        """
        if self.category not in ['Build', 'Deploy']:
            return []
        input_artifacts = [
            _codepipeline.CfnPipeline.InputArtifactProperty(
                name=self._get_base_input_artifact_name(),
            ),
        ]
        if self.category == 'Deploy':
            for override in (
                self.target
                .get('properties', {})
                .get('param_overrides', [])
            ):
                override_input = (
                    _codepipeline.CfnPipeline.InputArtifactProperty(
                        name=override.get('inputs', '')
                    )
                )
                requires_input_override = (
                    self.provider == "CloudFormation"
                    and override.get('inputs')
                    and self.action_mode != "CHANGE_SET_EXECUTE"
                    and override_input not in input_artifacts
                )

                if requires_input_override:
                    input_artifacts.append(override_input)
        return input_artifacts

    def _get_base_output_artifact_name(self):
        """
        Determine the name for the output artifact for this action.

        Returns:
            str: The output artifact name as a string
        """
        if self.category == 'Source':
            return "output-source"
        if self.category == 'Build' and not self.target:
            return f"{self.map_params['name']}-build"
        if self.category == 'Deploy' and self.provider == "CloudFormation":
            outputs_name = self.target.get('properties', {}).get('outputs', '')
            if outputs_name and self.action_mode != 'CHANGE_SET_REPLACE':
                return outputs_name
        return ''

    def _get_output_artifacts(self):
        """
        Generate the list of output artifacts that are required for this action

        Returns:
            list<CfnPipeline.OutputArtifactProperty>: The Output Artifacts
        """
        output_artifact_name = self._get_base_output_artifact_name()
        if output_artifact_name:
            return [
                _codepipeline.CfnPipeline.OutputArtifactProperty(
                    name=output_artifact_name
                ),
            ]
        return []


class Pipeline(Construct):
    _import_arns = [
        'CodePipelineRoleArn',
        'CodeBuildRoleArn',
        'SendSlackNotificationLambdaArn'
    ]

    CODEARTIFACT_TRIGGER = "CODEARTIFACT"

    _accepted_triggers = {"code_artifact": CODEARTIFACT_TRIGGER}

    # pylint: disable=W0622
    def __init__(
        self,
        scope: Construct,
        id: str,
        map_params: dict,
        ssm_params: dict,
        stages, **kwargs,
    ):
        super().__init__(scope, id, **kwargs)
        # pylint: disable=W0632
        [
            _codepipeline_role_arn,
            _code_build_role_arn,
            _send_slack_notification_lambda_arn
        ] = Pipeline.import_required_arns()
        pipeline_args = {
            "role_arn": _codepipeline_role_arn,
            "restart_execution_on_update": (
                map_params
                .get('params', {})
                .get('restart_execution_on_update', False)
            ),
            "name": f"{ADF_PIPELINE_PREFIX}{map_params['name']}",
            "stages": stages,
            "artifact_stores": Pipeline.generate_artifact_stores(
                map_params,
                ssm_params,
            ),
            "tags": Pipeline.restructure_tags(map_params.get('tags', {}))
        }
        self.default_scm_branch = map_params.get(
            "default_scm_branch",
            ADF_DEFAULT_SCM_FALLBACK_BRANCH,
        )
        self.cfn = _codepipeline.CfnPipeline(
            self,
            'pipeline',
            **pipeline_args
        )
        adf_events.Events(self, 'events', {
            "pipeline": (
                f'arn:{ADF_DEPLOYMENT_PARTITION}:codepipeline:'
                f'{ADF_DEPLOYMENT_REGION}:{ADF_DEPLOYMENT_ACCOUNT_ID}:'
                f'{os.getenv("ADF_PIPELINE_PREFIX")}{map_params["name"]}'
            ),
            "topic_arn": map_params.get('topic_arn'),
            "name": map_params['name'],
            "completion_trigger": (
                map_params
                .get('triggers', {})
                .get('on_complete', map_params.get('completion_trigger'))
            ),
            "schedule": map_params.get('schedule'),
            "source": {
                "provider": (
                    map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('provider')
                ),
                "account_id": (
                    map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('account_id')
                ),
                "repo_name": (
                    map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('repository', map_params['name'])
                ),
                "branch": (
                    map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('branch', self.default_scm_branch)
                ),
                "poll_for_changes": (
                    map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('poll_for_changes', False)
                ),
                "trigger_on_changes": (
                    map_params
                    .get('default_providers', {})
                    .get('source', {})
                    .get('properties', {})
                    .get('trigger_on_changes', True)
                ),
            }
        })

    @staticmethod
    def restructure_tags(current_tags):
        tags = []
        for key, value in current_tags.items():
            tags.append({
                "key": key,
                "value": value
            })
        return tags

    @staticmethod
    def generate_artifact_stores(map_params, ssm_params):
        output = []
        for region in map_params["regions"]:
            artifact_store = _codepipeline.CfnPipeline.ArtifactStoreProperty(
                location=ssm_params[region]["s3"],
                type="S3",
                encryption_key=_codepipeline.CfnPipeline.EncryptionKeyProperty(
                    id=ssm_params[region]["kms"],
                    type="KMS"
                ),
            )
            output.append(
                _codepipeline.CfnPipeline.ArtifactStoreMapProperty(
                    artifact_store=artifact_store,
                    region=region,
                ),
            )
        return output

    @staticmethod
    def import_required_arns():
        output = []
        for arn in Pipeline._import_arns:
            # pylint: disable=no-value-for-parameter
            output.append(Fn.import_value(arn))
        return output

    def add_pipeline_trigger(self, trigger_type, trigger_config):
        if trigger_type not in self._accepted_triggers:
            LOGGER.error(
                f"{trigger_type} is not currently supported. "
                f"Supported values are: {self._accepted_triggers.keys()}"
            )
            raise Exception(
                f"{trigger_type} is not currently supported as "
                "a pipeline trigger"
            )
        trigger_type = self._accepted_triggers[trigger_type]

        if trigger_type == self.CODEARTIFACT_TRIGGER:
            details = {"repositoryName": trigger_config["repository"]}
            if trigger_config.get("package"):
                details["packageName"] = trigger_config["package"]
            _eventbridge.Rule(
                self,
                (
                    "codeartifact-pipeline-"
                    f"trigger-{trigger_config['repository']}"
                    f"-{trigger_config.get('package', 'all')}"
                ),
                event_pattern=_eventbridge.EventPattern(
                    source=["aws.codeartifact"],
                    detail_type=["CodeArtifact Package Version State Change"],
                    detail=details,
                ),
                targets=[
                    _eventbridge_targets.CodePipeline(
                        pipeline=_codepipeline.Pipeline.from_pipeline_arn(
                            self,
                            "imported",
                            pipeline_arn=self.cfn.ref
                        )
                    )
                ],
            )
