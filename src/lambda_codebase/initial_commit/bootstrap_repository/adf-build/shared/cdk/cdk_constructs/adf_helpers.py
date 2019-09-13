import os
from logger import configure_logger
from aws_cdk import (
    aws_ssm as _ssm,
    core
)

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
AWS_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20

LOGGER = configure_logger(__name__)

class Helpers():
    @staticmethod
    def fetch_required_ssm_params(scope, regions):
        output = {}
        for region in regions:
            output[region] = {
                "s3": _ssm.StringParameter.from_string_parameter_attributes(
                    scope,
                    'S3Bucket{0}'.format(region),
                    parameter_name='/cross_region/s3_regional_bucket/{0}'.format(region)
                    ).string_value,
                "kms": _ssm.StringParameter.from_string_parameter_attributes(
                    scope,
                    'KMSKey{0}'.format(region), 
                    parameter_name='/cross_region/kms_arn/{0}'.format(region)
                    ).string_value,
            }
        output[ADF_DEPLOYMENT_REGION]["modules"] = _ssm.StringParameter.from_string_parameter_attributes(
            scope, 
            'deployment_account_bucket',
            parameter_name='deployment_account_bucket'
            ).string_value
        return output
