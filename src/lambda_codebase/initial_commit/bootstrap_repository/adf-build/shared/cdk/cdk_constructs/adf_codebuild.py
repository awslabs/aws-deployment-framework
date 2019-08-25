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

from cdk_constructs.adf_codepipeline import Action

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]
ADF_DEFAULT_SOURCE_ROLE = os.environ["ADF_DEFAULT_SOURCE_ROLE"]
ADF_DEFAULT_BUILD_ROLE = os.environ["ADF_DEFAULT_BUILD_ROLE"]
ADF_DEFAULT_BUILD_TIMEOUT = 20


class CodeBuild(core.Construct):
    def __init__(self, scope: core.Construct, id: str, shared_modules_bucket: str, deployment_region_kms: str, map_params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)
        _env = _codebuild.BuildEnvironment(
            build_image=_codebuild.LinuxBuildImage.UBUNTU_14_04_PYTHON_3_7_1,
            compute_type=_codebuild.ComputeType.SMALL,
            environment_variables=CodeBuild.generate_build_env_variables(_codebuild, shared_modules_bucket, map_params['name']),
            privileged=True
        )
        _codebuild.PipelineProject(
            self,
            'project',
            environment=_env,
            encryption_key=_kms.Key.from_key_arn(self, 'DefaultDeploymentAccountKey', key_arn=deployment_region_kms),
            description="ADF CodeBuild Project for {0}".format(map_params['name']),
            project_name="adf-build-{0}".format(map_params['name']),
            timeout=core.Duration.minutes(ADF_DEFAULT_BUILD_TIMEOUT),
            role=_iam.Role.from_role_arn(self, 'DefaultBuildRole', role_arn=ADF_DEFAULT_BUILD_ROLE)
        )
        self.build = _codepipeline.CfnPipeline.StageDeclarationProperty(
                name="Build",
                actions=[
                    Action(
                        name="Build",
                        provider="CodeBuild",
                        category="Build",
                        run_order=1,
                        map_params=map_params,
                        action_name="build"
                    ).config
                ]
            )

    @staticmethod
    def generate_build_env_variables(codebuild, shared_modules_bucket, name):
        return {
            "PYTHONPATH": codebuild.BuildEnvironmentVariable(value='./adf-build/python'), 
            "ADF_PROJECT_NAME": codebuild.BuildEnvironmentVariable(value=name),
            "S3_BUCKET_NAME": codebuild.BuildEnvironmentVariable(value=shared_modules_bucket),
            "ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=core.Aws.ACCOUNT_ID)
        }

