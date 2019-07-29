import os
from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_codepipeline_actions as _codepipeline_actions,
    aws_s3 as _s3,
    aws_iam as _iam,
    core
)

ADF_DEPLOYMENT_REGION = os.environ["ADF_DEPLOYMENT_REGION"]

def generate_regional_bucket_config(self, parameter_store, regions):
    output = {}
    for region in regions:
        output[region] = _s3.Bucket.from_bucket_name(
            self, 
            'deployment_{0}_bucket'.format(region), 
            bucket_name=parameter_store.fetch_parameter('/cross_region/s3_regional_bucket/{0}'.format(region))
        )
    return output

class Pipeline(core.Construct):
    def __init__(self, scope: core.Construct, id: str, params: dict, **kwargs):
        super().__init__(scope, id, **kwargs)

        # _artifact_bucket = _s3.Bucket.from_bucket_name(self, 'deployment_region_bucket', 
        #     bucket_name = params['parameter_store_client'].fetch_parameter('/cross_region/s3_regional_bucket/{0}'.format(os.environ["ADF_DEPLOYMENT_REGION"]))
        # )
        _iam_role = _iam.Role.from_role_arn(self, 'ADFCodePipelineRole', 
            role_arn="arn:aws:iam::{0}:role/{1}".format(os.environ["ADF_DEPLOYMENT_ACCOUNT_ID"], os.environ["ADF_CODEPIPELINE_ROLE"])
        )

        _regions_config = generate_regional_bucket_config(self, params['parameter_store_client'], params['regions'])
        pipeline = _codepipeline.Pipeline(self, "Pipeline",
            role=_iam_role,
            cross_region_replication_buckets=_regions_config,
            restart_execution_on_update=params.get('restart_execution_on_update', False),
            pipeline_name=params['pipeline_name']
        )

        # Source
        # _source_action_props = _codepipeline.ActionProperties(
        #     outputs="source",
        #     region=ADF_DEPLOYMENT_REGION,
        #     version=1,
        #     action_name="Source-{0}".format(params["SourceAccountId"]),
        #     owner="AWS",
        #     provider="CodeCommit",
        #     category="Source"
        # )

        # # Build
        # _build_action_props = _codepipeline.ActionProperties(
        #     inputs="source",
        #     outputs="built_outputs",
        #     region=ADF_DEPLOYMENT_REGION,
        #     version=1,
        #     action_name="Build",
        #     owner="AWS",
        #     provider="CodeBuild",
        #     category="Build"
        # )
        
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
                
                # pipeline.add_stage(
                #     stage_name='deployment-stage-{0}'.format(index),
                # )