import os
from logger import configure_logger
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
AWS_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20

LOGGER = configure_logger(__name__)

class Helpers(core.Construct):
    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

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
