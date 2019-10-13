# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Schema Validation for Deployment map files
"""

from schema import Schema, And, Use, Or, Optional, SchemaError
from logger import configure_logger

LOGGER = configure_logger(__name__)

# Pipeline Params
PARAM_SCHEMA = {
    Optional("notification_endpoint"): str,
    Optional("schedule"): str,
    Optional("restart_execution_on_update"): bool,
}

# CodeCommit Source
CODECOMMIT_SOURCE_PROPS = {
    "account_id": Schema(And(Use(int), lambda n: len(str(n)) == 12)),
    Optional("repository"): str,
    Optional("branch"): str,
    Optional("poll_for_changes"): bool,
    Optional("owner"): str,
    Optional("role"): str
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
    "json_field": str
}
GITHUB_SOURCE = {
    "provider": 'github',
    "properties": GITHUB_SOURCE_PROPS
}

# S3 Source
S3_SOURCE_PROPS = {
    "account_id": And(Use(int), lambda n: len(str(n)) == 12),
    "bucket_name": str,
    "object_key": str
}
S3_SOURCE = {
    "provider": 's3',
    "properties": S3_SOURCE_PROPS
}

# CodeBuild
CODEBUILD_PROPS = {
    Optional("image"): str,
    Optional("size"): Or('small', 'medium', 'large'),
    Optional("spec_filename"): str,
    Optional("environment_variables"): {Optional(str): Or(str, bool, int, object)},
    Optional("role"): str,
    Optional("timeout"): int,
    Optional("privileged"): bool,
    Optional("spec_inline"): str
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
PROVIDER_SCHEMA = {
        'source': Or(CODECOMMIT_SOURCE, GITHUB_SOURCE, S3_SOURCE),
        Optional('build'): Or(DEFAULT_CODEBUILD_BUILD, JENKINS_BUILD),
        Optional('deploy'): Or(DEFAULT_CLOUDFORMATION_DEPLOY, DEFAULT_S3_DEPLOY, DEFAULT_CODEDEPLOY_DEPLOY, DEFAULT_LAMBDA_INVOKE, DEFAULT_SERVICECATALOG_DEPLOY, DEFAULT_CODEBUILD_BUILD)
}
REGION_SCHEMA = Or(
    str,
    list
)
TARGET_SCHEMA = {
    Optional("path"): Or(str, int),
    Optional("target"): Or(str, int),
    Optional("name"): str,
    Optional("provider"): Or('lambda', 's3', 'codedeploy', 'cloudformation', 'service_catalog', 'approval', 'codebuild', 'jenkins'),
    Optional("properties"): Or(CODEBUILD_PROPS, JENKINS_PROPS, CLOUDFORMATION_PROPS, CODEDEPLOY_PROPS, S3_DEPLOY_PROPS, SERVICECATALOG_PROPS, LAMBDA_PROPS, APPROVAL_PROPS),
    Optional("regions"): REGION_SCHEMA
}
COMPLETION_TRIGGERS_SCHEMA = {
    "pipelines": [str]
}
PIPELINE_SCHEMA = {
    "name": And(str, len),
    "default_providers": PROVIDER_SCHEMA,
    Optional("params"): PARAM_SCHEMA,
    Optional("targets"): [Or(str, int, TARGET_SCHEMA)],
    Optional("regions"): REGION_SCHEMA,
    Optional("completion_trigger"): COMPLETION_TRIGGERS_SCHEMA
}
TOP_LEVEL_SCHEMA = {
    "pipelines": [PIPELINE_SCHEMA]
}

class SchemaValidation:
    def __init__(self, map_input: dict):
        self.validated = Schema(TOP_LEVEL_SCHEMA).validate(map_input)

    @staticmethod
    def extract_key_from_schema_error(e: SchemaError) -> str:
        return str(e).split(" ")[1].strip("'")
