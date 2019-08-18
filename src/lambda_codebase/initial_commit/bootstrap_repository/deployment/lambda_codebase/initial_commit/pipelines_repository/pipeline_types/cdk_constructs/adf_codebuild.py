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


class CodeBuild(core.Construct):
    def __init__(self, scope: core.Construct, id: str, shared_modules_bucket: str, deployment_region_kms: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        _env = _codebuild.BuildEnvironment(
            build_image=_codebuild.LinuxBuildImage.UBUNTU_14_04_PYTHON_3_7_1,
            compute_type=_codebuild.ComputeType.SMALL,
            environment_variables=CodeBuild.generate_build_env_variables(_codebuild, shared_modules_bucket),
            privileged=True
        )
        _codebuild.PipelineProject(
            self,
            'Project',
            environment=_env,
            encryption_key=_kms.Key.from_key_arn(self, 'DefaultDeploymentAccountKey', key_arn=deployment_region_kms),
            description="ADF CodeBuild Project for {0}".format(ADF_PROJECT_NAME),
            project_name="adf-build-{0}".format(ADF_PROJECT_NAME),
            timeout=core.Duration.minutes(ADF_DEFAULT_BUILD_TIMEOUT),
            role=_iam.Role.from_role_arn(self, 'DefaultBuildRole', role_arn=ADF_DEFAULT_BUILD_ROLE)
        )

    @staticmethod
    def generate_build_env_variables(codebuild, shared_modules_bucket):
        return {
            "PYTHONPATH": codebuild.BuildEnvironmentVariable(value='./adf-build/python'), 
            "ADF_PROJECT_NAME": codebuild.BuildEnvironmentVariable(value=ADF_PROJECT_NAME),
            "S3_BUCKET_NAME": codebuild.BuildEnvironmentVariable(value=shared_modules_bucket),
            "ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=core.Aws.ACCOUNT_ID)
        }

    # @staticmethod
    # def generate_action():
    #     return [
    #         _codepipeline.CfnPipeline.ActionDeclarationProperty(
    #             action_type_id=_codepipeline.CfnPipeline.ActionTypeIdProperty(
    #                 version="1",
    #                 owner="AWS",
    #                 provider="CodeBuild",
    #                 category="Build"
    #             ),
    #             configuration={
    #                 "ProjectName": "adf-build-{0}".format(ADF_PROJECT_NAME)
    #             },
    #             name="build",
    #             region=ADF_DEPLOYMENT_REGION,
    #             output_artifacts=[_codepipeline.CfnPipeline.OutputArtifactProperty(
    #                 name="build-{0}".format(ADF_PROJECT_NAME)
    #             )],
    #             input_artifacts=[_codepipeline.CfnPipeline.InputArtifactProperty(
    #                 name="source"
    #             )],
    #             run_order=1
    #         )
    #     ]