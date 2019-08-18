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
ADF_PROJECT_NAME = os.environ["ADF_PROJECT_NAME"]
AWS_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
ADF_DEFAULT_BUILD_TIMEOUT = 20

LOGGER = configure_logger(__name__)

# def parameter_normalization(map_params):
#     if not map_params.get('type'):
#         LOGGER.info(
#             'type is not set explicitly, setting codecommit, '
#             'codebuild and cloudformation as defaults. '
#             'These will be overridden if specified in the targets section.'
#         )
#         map_params['type'] = {
#             "source": "codecommit",
#             "build": "codebuild",
#             "deploy": "cloudformation"
#         }
#     if not map_params.get('regions'):
#         LOGGER.info('regions is not set explicitly, setting {0} as default.'.format(ADF_DEPLOYMENT_REGION))
#         map_params['regions'] = [ADF_DEPLOYMENT_REGION]
#     else:
#         if isinstance(map_params.get('regions'), list):
#             map_params['regions'] = [map_params.get('regions')]
#     if not map_params.get('type', {}).get("source"):
#         LOGGER.info('source is not set explicitly, setting codecommit as default.')
#         map_params['type']["source"] = "codecommit"
#     if not map_params.get('type', {}).get("build"):
#         LOGGER.info('build is not set explicitly, setting codebuild as default.')
#         map_params['type']["build"] = "codebuild"
#     if not map_params.get('type', {}).get("deploy"):
#         LOGGER.info('deploy is not set explicitly, setting cloudformation as default.')
#         map_params['type']["build"] = "codebuild"
#     if not map_params.get("source_account_id") and map_params['type'].get('source') == 'codecommit':
#         LOGGER.info('source_account_id is not set explicitly, setting {0} as default.'.format(AWS_ACCOUNT_ID))
#         map_params["source_account_id"] = AWS_ACCOUNT_ID
#     if map_params.get('type', {}).get("source") == 'github':
#         try:
#             assert map_params['params'].get('repository_owner')
#             assert map_params['params'].get('oauth_token')
#             assert map_params['params'].get('webhook_secret')
#         except AssertionError as error:
#             # TODO invalidaDeploymentMapError
#             raise Exception("Invalid Deployment Map : {0}".format(error))

    #return map_params

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
