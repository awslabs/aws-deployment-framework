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

def import_required_arns(import_arns):
    output = []
    for arn in import_arns:
        output.append(core.Fn.import_value(arn))
    return output

def fetch_required_ssm_params(self, regions):
    output = {}
    for region in regions:
        output[region] = {
            "s3": _ssm.StringParameter.from_string_parameter_attributes(
                    self, 
                    'S3Bucket{0}'.format(region), 
                    parameter_name='S3Bucket{0}'.format(region)
                ),
            "kms": _ssm.StringParameter.from_string_parameter_attributes(
                    self, 
                    'KMSKey{0}'.format(region), 
                    parameter_name='KMSKey{0}'.format(region)
                )
        }
    return output

def generate_build_env_variables(codebuild):
    codebuild.BuildEnvironmentVariable.value = [{"Name": "test"}]
    return codebuild

class Pipeline(core.Construct):
    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)

        [_codepipeline_role_arn, _code_build_role_arn, _send_slack_notification_lambda_arn] = import_required_arns(import_arns)
        _ssm_parameters = fetch_required_ssm_params(self, params['regions'])
        # _artifact_bucket = _s3.Bucket.from_bucket_name(self, 'deployment_region_bucket', 
        #     bucket_name = params['parameter_store_client'].fetch_parameter('/cross_region/s3_regional_bucket/{0}'.format(os.environ["ADF_DEPLOYMENT_REGION"]))
        # )
        _pipeline_args = {
            "role": _codepipeline_role_arn,
            "restart_execution_on_update": params.get('restart_execution_on_update', False),
            "pipeline_name": params['name']
        }
        if len(params['regions']) > 1:
            _cross_region_buckets = { region:d["s3"] for [ region, d ] in fetch_required_ssm_params(self, params['regions']).items() }
            _pipeline_args['cross_region_replication_buckets'] = _cross_region_buckets

        print(**_pipeline_args)
        # _artifact = _codepipeline.Artifact(artifact_name=ADF_PROJECT_NAME)
        pipeline = _codepipeline.Pipeline(self, "Pipeline",
            **_pipeline_args
        )
        _source = _codepipeline_actions.CodeCommitSourceAction(
            branch=params.get('branch_name', 'master'),
            action_name="Source",
            repository=params.get('project_name', params.get('repository_name')),
            run_order=1,
            role=params.get('source_role', ADF_DEFAULT_SOURCE_ROLE),
            output=["source"]
        )
        _env = _codebuild.BuildEnvironment(
            build_image=params.get('image', _codebuild.LinuxBuildImage.UBUNTU_14_04_PYTHON_3_7_1),
            compute_type=params.get('compute_type', _codebuild.ComputeType.SMALL),
            environment_variables=generate_build_env_variables(_codebuild),
            privileged=True
        )
        _project = _codebuild.PipelineProject(self, 'Project', 
            environment=_env,
            encryption_key=_ssm_parameters["KMSKey{0}".format(ADF_DEPLOYMENT_REGION)],
            allow_all_outbound=True,
            description="ADF CodeBuild Project for {0}".format(ADF_PROJECT_NAME),
            project_name=ADF_PROJECT_NAME,
            timeout=ADF_DEFAULT_BUILD_TIMEOUT,
            role=_code_build_role_arn
        )
        _build = _codepipeline_actions.CodeBuildAction(
            action_name="Build",
            input="source",
            project=_project,
            outputs="{0}-build".format(ADF_PROJECT_NAME),
            type=_codepipeline_actions.CodeBuildActionType.BUILD,
            role=params.get('build_role', ADF_DEFAULT_BUILD_ROLE),
            run_order=1
        )
        pipeline.add_stage(
            actions=[_source],
            stage_name="Source"
        )
        pipeline.add_stage(
            actions=[_build],
            stage_name="Build"
        )
        
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