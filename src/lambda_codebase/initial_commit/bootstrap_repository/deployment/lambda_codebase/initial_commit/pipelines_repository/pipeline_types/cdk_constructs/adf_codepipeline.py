import os
from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_codepipeline_actions as _codepipeline_actions,
    aws_codecommit as _codecommit,
    aws_codebuild as _codebuild,
    aws_s3 as _s3,
    aws_iam as _iam,
    aws_kms as _kms,
    aws_ssm as _ssm,
    core
)

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]
ADF_DEFAULT_SOURCE_ROLE = os.environ["ADF_DEFAULT_SOURCE_ROLE"]
ADF_DEFAULT_BUILD_ROLE = os.environ["ADF_DEFAULT_BUILD_ROLE"]
ADF_PROJECT_NAME = os.environ["ADF_PROJECT_NAME"]
ADF_DEFAULT_BUILD_TIMEOUT = 20

import_arns = [
    'CodePipelineRoleArn',
    'CodeBuildRoleArn',
    'SendSlackNotificationLambdaArn'
]

def import_required_arns(_import_arns):
    output = []
    for arn in _import_arns:
        output.append(core.Fn.import_value(arn))
    return output

def fetch_required_ssm_params(self, regions):
    output = {}
    for region in regions:
        output[region] = {
            "s3": _ssm.StringParameter.from_string_parameter_attributes(
                    self,
                    'S3Bucket{0}'.format(region),
                    parameter_name='/cross_region/s3_regional_bucket/{0}'.format(region)
                ).string_value,
            "kms": _ssm.StringParameter.from_string_parameter_attributes(
                    self,
                    'KMSKey{0}'.format(region), 
                    parameter_name='/cross_region/kms_arn/{0}'.format(region)
                ).string_value,
        }
    output[ADF_DEPLOYMENT_REGION]["modules"] = _ssm.StringParameter.from_string_parameter_attributes(
                    self, 
                    'deployment_account_bucket', 
                    parameter_name='deployment_account_bucket'
                ).string_value
    return output

def generate_build_env_variables(codebuild, shared_modules_bucket):
    return {
        "PYTHONPATH": codebuild.BuildEnvironmentVariable(value='./adf-build/python'), 
        "ADF_PROJECT_NAME": codebuild.BuildEnvironmentVariable(value=ADF_PROJECT_NAME),
        "S3_BUCKET_NAME": codebuild.BuildEnvironmentVariable(value=shared_modules_bucket),
        "ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=core.Aws.ACCOUNT_ID)
    }

def generate_stages(self, params, _env):
    return [
        _codepipeline.CfnPipeline.StageDeclarationProperty(
            name='Source',
            actions=[
                _codepipeline.CfnPipeline.ActionDeclarationProperty(
                action_type_id=_codepipeline.CfnPipeline.ActionTypeIdProperty(
                    version="1",
                    owner="AWS",
                    provider="CodeCommit",
                    category="Source"
                ),
                configuration={
                    "BranchName": params.get('branch', 'master'),
                    "RepositoryName": params.get('repository', ADF_PROJECT_NAME)
                },
                name="source",
                run_order=1,
                output_artifacts=[_codepipeline.CfnPipeline.OutputArtifactProperty(
                    name="source"
                )],
                role_arn=params.get('source_role', ADF_DEFAULT_SOURCE_ROLE),
            )]
        ),
        _codepipeline.CfnPipeline.StageDeclarationProperty(
            name='Build',
            actions=[_codepipeline.CfnPipeline.ActionDeclarationProperty(
                action_type_id=_codepipeline.CfnPipeline.ActionTypeIdProperty(
                    version="1",
                    owner="AWS",
                    provider="CodeBuild",
                    category="Build"
                ),
                configuration={
                    "ProjectName": "adf-build-{0}".format(ADF_PROJECT_NAME)
                },
                name="build",
                region=ADF_DEPLOYMENT_REGION,
                output_artifacts=[_codepipeline.CfnPipeline.OutputArtifactProperty(
                    name="build-{0}".format(ADF_PROJECT_NAME)
                )],
                input_artifacts=[_codepipeline.CfnPipeline.InputArtifactProperty(
                    name="source"
                )],
                run_order=1
            )
            ]
        )
    ]


def generate_artifact_stores(self, regions, parameters):
    output = []
    for region in regions:
        output.append(_codepipeline.CfnPipeline.ArtifactStoreMapProperty(
            artifact_store=_codepipeline.CfnPipeline.ArtifactStoreProperty(
                location=parameters[region]["s3"],
                type="S3",
                encryption_key=_codepipeline.CfnPipeline.EncryptionKeyProperty(
                    id=parameters[region]["kms"],
                    type="KMS"
                )
            ),
            region=region
        ))
    return output

class Pipeline(core.Construct):
    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)

        [_codepipeline_role_arn, _code_build_role_arn, _send_slack_notification_lambda_arn] = import_required_arns(import_arns)
        _ssm_parameters = fetch_required_ssm_params(self, params['regions'])
        _deployment_region_kms_key = _kms.Key.from_key_arn(self, "DeploymentAccountKey", key_arn=_ssm_parameters[ADF_DEPLOYMENT_REGION]["kms"])
        # _bucket = _s3.Bucket.from_bucket_name(self, 'ArtifactBucket', _ssm_parameters[ADF_DEPLOYMENT_REGION]["s3"])

        # _input_artifact = _codepipeline.Artifact(artifact_name=ADF_PROJECT_NAME)
        # _output_artifact = _codepipeline.Artifact(artifact_name="{0}-build".format(ADF_PROJECT_NAME))

        _env = _codebuild.BuildEnvironment(
            build_image=_codebuild.LinuxBuildImage.UBUNTU_14_04_PYTHON_3_7_1,
            compute_type=_codebuild.ComputeType.SMALL,
            environment_variables=generate_build_env_variables(_codebuild, _ssm_parameters[ADF_DEPLOYMENT_REGION]["modules"]),
            privileged=True
        )
        _build_role = _iam.Role.from_role_arn(
            self, 
            'DefaultBuildRole', 
            role_arn=ADF_DEFAULT_BUILD_ROLE
        )
        _project = _codebuild.PipelineProject(self, 'Project', 
            environment=_env,
            encryption_key=_deployment_region_kms_key,
            description="ADF CodeBuild Project for {0}".format(ADF_PROJECT_NAME),
            project_name="adf-build-{0}".format(ADF_PROJECT_NAME),
            timeout=core.Duration.minutes(ADF_DEFAULT_BUILD_TIMEOUT),
            role=_build_role
        )
        # _build = _codepipeline_actions.CodeBuildAction(
        #     action_name="Build",
        #     input=_input_artifact,
        #     project=_project,
        #     outputs=[_output_artifact],
        #     type=_codepipeline_actions.CodeBuildActionType.BUILD,
        #     run_order=1
        # )
        _pipeline_args = {
            "role_arn": _codepipeline_role_arn,
            "restart_execution_on_update": params.get('restart_execution_on_update', False),
            "name": params['name'],
            "stages": generate_stages(self, params, _env),
            "artifact_stores": generate_artifact_stores(self, params["regions"], _ssm_parameters)
        }

        if len(params['regions']) > 1:
            _cross_region_buckets = { region:d["s3"] for [ region, d ] in _ssm_parameters.items() }
            _pipeline_args['cross_region_replication_buckets'] = _cross_region_buckets

        print(_pipeline_args)
        pipeline = _codepipeline.CfnPipeline(self, "Pipeline",
            **_pipeline_args
        )
        pipeline._validate()
        
        

        # for stage, index in enumerate(params['stages']):
        #     _regions = stage.get('regions', params.get('top_level_regions', ADF_DEPLOYMENT_REGION))
        #     if not isinstance(_regions, list):
        #         _regions = [_regions]

        #     for _region in _regions:
        #         _action_props = _codepipeline.ActionProperties(
        #             region=_region,
        #             inputs="built_outputs",
        #             version=1,
        #             run_order=1,
        #             action_name="deployment_action_{0}".format(index),
        #             owner="AWS",
        #             provider="CloudFormation",
        #             category="Deploy"
        #         )
                
        #         pipeline.add_stage(
        #             stage_name='deployment-stage-{0}'.format(index),
        #         )