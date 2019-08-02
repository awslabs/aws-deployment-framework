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

def generate_codebuild_action():
    return [
        _codepipeline.CfnPipeline.ActionDeclarationProperty(
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