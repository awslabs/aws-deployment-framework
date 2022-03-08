# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Schema Validation for Deployment map files
"""

from schema import Schema, And, Use, Or, Optional, Regex
from logger import configure_logger

LOGGER = configure_logger(__name__)

NOTIFICATION_PROPS = {
    Optional("target"): str,
    Optional("type") : Or("lambda", "chat_bot")
}

# Pipeline Params
PARAM_SCHEMA = {
    Optional("notification_endpoint"): Or(str, NOTIFICATION_PROPS),
    Optional("schedule"): str,
    Optional("restart_execution_on_update"): bool,
    Optional("pipeline_type", default="default"): Or("default"),
}

AWS_ACCOUNT_ID_REGEX_STR = r"\A[0-9]{12}\Z"
AWS_ACCOUNT_ID_SCHEMA = Schema(
    And(
        Or(int, str),
        Use(str),
        Regex(
            AWS_ACCOUNT_ID_REGEX_STR,
            error=(
                "The specified account id is incorrect. "
                "This typically happens when you specify the account id as a "
                "number, while the account id starts with a zero. If this is "
                "the case, please wrap the account id in quotes to make it a "
                "string. An AWS Account Id is a number of 12 digits, which "
                "should start with a zero if the Account Id has a zero at "
                "the start too. "
                "The number shown to not match the regular expression could "
                "be interpreted as an octal number due to the leading zero. "
                "Therefore, it might not match the account id as specified "
                "in the deployment map."
            )
        )
    )
)

# CodeCommit Source
CODECOMMIT_SOURCE_PROPS = {
    "account_id": AWS_ACCOUNT_ID_SCHEMA,
    Optional("repository"): str,
    Optional("branch"): str,
    Optional("poll_for_changes"): bool,
    Optional("owner"): str,
    Optional("role"): str,
    Optional("trigger_on_changes"): bool,
    Optional("output_artifact_format", default=None): Or("CODEBUILD_CLONE_REF", "CODE_ZIP", None)
}
CODECOMMIT_SOURCE = {
    "provider": 'codecommit',
    "properties": CODECOMMIT_SOURCE_PROPS
}

# GitHub Source
GITHUB_SOURCE_PROPS = {
    Optional("repository"): str,
    Optional("branch"): str,
    "owner": str,
    "oauth_token_path": str,
    "json_field": str,
    Optional("trigger_on_changes"): bool,
}
GITHUB_SOURCE = {
    "provider": 'github',
    "properties": GITHUB_SOURCE_PROPS
}

# CodeStar Source
CODESTAR_SOURCE_PROPS = {
    Optional("repository"): str,
    Optional("branch"): str,
    "owner": str,
    "codestar_connection_path": str
}

CODESTAR_SOURCE = {
    "provider": 'codestar',
    "properties": CODESTAR_SOURCE_PROPS
}

# S3 Source
S3_SOURCE_PROPS = {
    "account_id": AWS_ACCOUNT_ID_SCHEMA,
    "bucket_name": str,
    "object_key": str,
    Optional("trigger_on_changes"): bool,
}
S3_SOURCE = {
    "provider": 's3',
    "properties": S3_SOURCE_PROPS
}

# CodeBuild
CODEBUILD_IMAGE_PROPS = {
    "repository_arn": str,  # arn:aws:ecr:region:111111111111:repository/test
    Optional("tag"): str,   # defaults to latest
}
CODEBUILD_PROPS = {
    Optional("image"): Or(str, CODEBUILD_IMAGE_PROPS),
    Optional("size"): Or('small', 'medium', 'large'),
    Optional("spec_filename"): str,
    Optional("environment_variables"): {Optional(str): Or(str, bool, int, object)},
    Optional("role"): str,
    Optional("timeout"): int,
    Optional("privileged"): bool,
    Optional("spec_inline"): object,
}
DEFAULT_CODEBUILD_BUILD = {
    Optional("provider"): 'codebuild',
    Optional("enabled"): bool,
    Optional("properties"): CODEBUILD_PROPS
}
STAGE_CODEBUILD_BUILD = {
    Optional("provider"): 'codebuild',
    Optional("properties"): CODEBUILD_PROPS
}

# Jenkins
JENKINS_PROPS = {
    Optional("project_name"): str,
    Optional("server_url"): str,
    Optional("provider_name"): str
}
JENKINS_BUILD = {
    Optional("provider"): 'jenkins',
    Optional("enabled"): bool,
    Optional("properties"): JENKINS_PROPS
}

# CloudFormation
PARAM_OVERRIDE_SCHEMA = {
    "inputs": str,
    "param": str,
    "key_name": str
}
CLOUDFORMATION_ACTIONS = Or(
        'CHANGE_SET_EXECUTE',
        'CHANGE_SET_REPLACE',
        'CREATE_UPDATE',
        'DELETE_ONLY',
        'REPLACE_ON_FAILURE',
        'change_set_execute',
        'change_set_replace',
        'create_update',
        'delete_only',
        'replace_on_failure'
    )

CLOUDFORMATION_PROPS = {
    Optional("stack_name"): str,
    Optional("template_filename"): str,
    Optional("root_dir"): str,
    Optional("role"): str,
    Optional("action"): CLOUDFORMATION_ACTIONS,
    Optional("outputs"): str,
    Optional("change_set_approval"): bool,
    Optional("param_overrides"): [PARAM_OVERRIDE_SCHEMA]
}
# No need for a stage schema since CFN takes all optional props
DEFAULT_CLOUDFORMATION_DEPLOY = {
    "provider": 'cloudformation',
    Optional("properties"): CLOUDFORMATION_PROPS
}

# CodeDeploy
CODEDEPLOY_PROPS = {
    "application_name": str,
    "deployment_group_name": str,
    Optional("role"): str
}
STAGE_CODEDEPLOY_DEPLOY = {
    Optional("provider"): 'codedeploy',
    "properties": CODEDEPLOY_PROPS
}
DEFAULT_CODEDEPLOY_DEPLOY = {
    "provider": 'codedeploy',
    Optional("properties"): CODEDEPLOY_PROPS
}

# S3
S3_DEPLOY_PROPS = {
    "bucket_name": str,
    "object_key": str,
    Optional("extract"): bool,
    Optional("role"): str
}
STAGE_S3_DEPLOY = {
    Optional("provider"): 's3',
    "properties": S3_DEPLOY_PROPS
}
DEFAULT_S3_DEPLOY = {
    "provider": 's3',
    Optional("properties"): S3_DEPLOY_PROPS
}

# Service Catalog
SERVICECATALOG_PROPS = {
    "product_id": str,
    Optional("configuration_file_path"): str
}
STAGE_SERVICECATALOG_DEPLOY = {
    Optional("provider"): 'service_catalog',
    "properties": SERVICECATALOG_PROPS
}
DEFAULT_SERVICECATALOG_DEPLOY = {
    "provider": 'service_catalog',
    Optional("properties"): SERVICECATALOG_PROPS
}

# Lambda
LAMBDA_PROPS = {
    "function_name": str,
    Optional("input"): Or(str, object),
    Optional("role"): str
}
STAGE_LAMBDA_INVOKE = {
    Optional("provider"): 'lambda',
    "properties": LAMBDA_PROPS
}
DEFAULT_LAMBDA_INVOKE = {
    "provider": 'lambda',
    Optional("properties"): LAMBDA_PROPS
}

# Approval
APPROVAL_PROPS = {
    Optional("message"): str,
    Optional("notification_endpoint"): str,
    Optional("sns_topic_arn"): str
}
DEFAULT_APPROVAL = {
    "provider": 'approval',
    "properties": APPROVAL_PROPS
}

# Core Schema
PROVIDER_SOURCE_SCHEMAS = {
    'codecommit': Schema(CODECOMMIT_SOURCE),
    'github': Schema(GITHUB_SOURCE),
    's3': Schema(S3_SOURCE),
    'codestar': Schema(CODESTAR_SOURCE),
}
PROVIDER_BUILD_SCHEMAS = {
    'codebuild': Schema(DEFAULT_CODEBUILD_BUILD),
    'jenkins': Schema(JENKINS_BUILD),
}
PROVIDER_DEPLOY_SCHEMAS = {
    'cloudformation': Schema(DEFAULT_CLOUDFORMATION_DEPLOY),
    's3': Schema(DEFAULT_S3_DEPLOY),
    'codedeploy': Schema(DEFAULT_CODEDEPLOY_DEPLOY),
    'lambda': Schema(DEFAULT_LAMBDA_INVOKE),
    'service_catalog': Schema(DEFAULT_SERVICECATALOG_DEPLOY),
    'codebuild': Schema(DEFAULT_CODEBUILD_BUILD),
}
PROVIDER_SCHEMA = {
    'source': And(
        {
            'provider': Or('codecommit', 'github', 's3', 'codestar'),
            'properties': dict,
        },
        lambda x: PROVIDER_SOURCE_SCHEMAS[x['provider']].validate(x),  #pylint: disable=W0108
    ),
    Optional('build'): And(
        {
            Optional('provider'): Or('codebuild', 'jenkins'),
            Optional('enabled'): bool,
            Optional('properties'): dict,
        },
        lambda x: PROVIDER_BUILD_SCHEMAS[x.get('provider', 'codebuild')].validate(x),  #pylint: disable=W0108
    ),
    Optional('deploy'): And(
        {
            'provider': Or(
                'cloudformation', 's3', 'codedeploy', 'lambda',
                'service_catalog', 'codebuild'
            ),
            Optional('enabled'): bool,
            Optional('properties'): dict,
        },
        lambda x: PROVIDER_DEPLOY_SCHEMAS[x['provider']].validate(x),  #pylint: disable=W0108
    ),
}
REGION_SCHEMA = Or(
    str,
    list
)

TARGET_LIST_SCHEMA = [Or(
    str,
    int
)]

TARGET_WAVE_SCHEME = {
    Optional("size", default=50): int,
}

# Pipeline Params

TARGET_SCHEMA = {
    Optional("path"): Or(str, int, TARGET_LIST_SCHEMA),
    Optional("tags"): {And(str, Regex(r"\A.{1,128}\Z")): And(str, Regex(r"\A.{0,256}\Z"))},
    Optional("target"): Or(str, int, TARGET_LIST_SCHEMA),
    Optional("name"): str,
    Optional("provider"): Or('lambda', 's3', 'codedeploy', 'cloudformation', 'service_catalog', 'approval', 'codebuild', 'jenkins'),
    Optional("properties"): Or(CODEBUILD_PROPS, JENKINS_PROPS, CLOUDFORMATION_PROPS, CODEDEPLOY_PROPS, S3_DEPLOY_PROPS, SERVICECATALOG_PROPS, LAMBDA_PROPS, APPROVAL_PROPS),
    Optional("regions"): REGION_SCHEMA,
    Optional("exclude", default=[]): [str],
    Optional("wave", default={"size": 50}): TARGET_WAVE_SCHEME
}
COMPLETION_TRIGGERS_SCHEMA = {
    "pipelines": [str]
}
PIPELINE_TRIGGERS_SCHEMA = {
    Optional("code_artifact"): {
      "repository": str,
      Optional("package"): str,
    }
}
TRIGGERS_SCHEMA = {
    Optional("on_complete"): COMPLETION_TRIGGERS_SCHEMA,
    Optional("triggered_by"): [PIPELINE_TRIGGERS_SCHEMA],
}
PIPELINE_SCHEMA = {
    "name": And(str, len),
    "default_providers": PROVIDER_SCHEMA,
    Optional("params"): PARAM_SCHEMA,
    Optional("tags"): dict,
    Optional("targets"): [Or(str, int, TARGET_SCHEMA, TARGET_LIST_SCHEMA)],
    Optional("regions"): REGION_SCHEMA,
    Optional("completion_trigger"): COMPLETION_TRIGGERS_SCHEMA,
    Optional("triggers"): TRIGGERS_SCHEMA
}
TOP_LEVEL_SCHEMA = {
    "pipelines": [PIPELINE_SCHEMA],
    # Allow any toplevel key starting with "x-" or "x_".
    # ADF will ignore these, but users can use them to define anchors in one place.
    Optional(Regex('^[x][-_].*')): object
}

class SchemaValidation:
    def __init__(self, map_input: dict):
        self.validated = Schema(TOP_LEVEL_SCHEMA).validate(map_input)
