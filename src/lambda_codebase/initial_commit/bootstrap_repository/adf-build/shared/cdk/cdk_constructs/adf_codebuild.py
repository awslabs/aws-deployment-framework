# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to CodeBuild Input
"""

import os
from aws_cdk import (
    aws_codepipeline as _codepipeline,
    aws_codebuild as _codebuild,
    aws_iam as _iam,
    aws_kms as _kms,
    aws_ecr as _ecr,
    core
)

from cdk_constructs.adf_codepipeline import Action

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
DEFAULT_CODEBUILD_IMAGE = "UBUNTU_14_04_PYTHON_3_7_1"

class CodeBuild(core.Construct):
    # pylint: disable=no-value-for-parameter

    def __init__(self, scope: core.Construct, id: str, shared_modules_bucket: str, deployment_region_kms: str, map_params: dict, target, **kwargs): #pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        ADF_DEFAULT_BUILD_ROLE = 'arn:aws:iam::{0}:role/adf-codebuild-role'.format(ADF_DEPLOYMENT_ACCOUNT_ID)
        ADF_DEFAULT_BUILD_TIMEOUT = 20
        # if CodeBuild is being used as a deployment action we want to allow target specific values.
        if target:
            _build_role = 'arn:aws:iam::{0}:role/{1}'.format(
                ADF_DEPLOYMENT_ACCOUNT_ID,
                target.get('properties', {}).get('role')
            ) if target.get('properties', {}).get('role') else ADF_DEFAULT_BUILD_ROLE
            _timeout = target.get('properties', {}).get('timeout') or ADF_DEFAULT_BUILD_TIMEOUT
            _env = _codebuild.BuildEnvironment(
                build_image=CodeBuild.determine_build_image(scope, target, map_params),
                compute_type=target.get(
                    'properties', {}).get(
                        'size') or getattr(
                            _codebuild.ComputeType, map_params['default_providers']['build'].get(
                                'properties', {}).get(
                                    'size', "SMALL").upper()),
                environment_variables=CodeBuild.generate_build_env_variables(_codebuild, shared_modules_bucket, map_params, target),
                privileged=target.get('properties', {}).get('privileged', False) or map_params['default_providers']['build'].get('properties', {}).get('privileged', False)
            )
            _spec_filename = (
                target.get('properties', {}).get('spec_filename') or
                map_params['default_providers']['deploy'].get('properties', {}).get('spec_filename') or
                'deployspec.yml'
            )
            _codebuild.PipelineProject(
                self,
                'project',
                environment=_env,
                encryption_key=_kms.Key.from_key_arn(self, 'default_deployment_account_key', key_arn=deployment_region_kms),
                description="ADF CodeBuild Project for {0}".format(id),
                project_name="adf-deploy-{0}".format(id),
                timeout=core.Duration.minutes(_timeout),
                role=_iam.Role.from_role_arn(self, 'build_role', role_arn=_build_role, mutable=False),
                build_spec=_codebuild.BuildSpec.from_source_filename(_spec_filename)
            )
            self.deploy = Action(
                name="{0}".format(id),
                provider="CodeBuild",
                category="Build",
                project_name="adf-deploy-{0}".format(id),
                run_order=1,
                target=target,
                map_params=map_params,
                action_name="{0}".format(id)
            ).config
        else:
            _build_role = 'arn:aws:iam::{0}:role/{1}'.format(
                ADF_DEPLOYMENT_ACCOUNT_ID,
                map_params['default_providers']['build'].get('properties', {}).get('role')
            ) if map_params['default_providers']['build'].get('properties', {}).get('role') else ADF_DEFAULT_BUILD_ROLE
            _timeout = map_params['default_providers']['build'].get('properties', {}).get('timeout') or ADF_DEFAULT_BUILD_TIMEOUT
            _env = _codebuild.BuildEnvironment(
                build_image=CodeBuild.determine_build_image(scope, target, map_params),
                compute_type=getattr(_codebuild.ComputeType, map_params['default_providers']['build'].get('properties', {}).get('size', "SMALL").upper()),
                environment_variables=CodeBuild.generate_build_env_variables(_codebuild, shared_modules_bucket, map_params),
                privileged=map_params['default_providers']['build'].get('properties', {}).get('privileged', False)
            )
            if map_params['default_providers']['build'].get('properties', {}).get('role'):
                ADF_DEFAULT_BUILD_ROLE = 'arn:aws:iam::{0}:role/{1}'.format(ADF_DEPLOYMENT_ACCOUNT_ID, map_params['default_providers']['build'].get('properties', {}).get('role'))
            _build_stage_spec = map_params['default_providers']['build'].get('properties', {}).get('spec_filename')
            _build_inline_spec = map_params['default_providers']['build'].get(
                'properties', {}).get(
                    'spec_inline', '') or map_params['default_providers']['build'].get(
                        'properties', {}).get(
                            'spec_inline', '')
            if _build_stage_spec:
                _spec = _codebuild.BuildSpec.from_source_filename(_build_stage_spec)
            elif _build_inline_spec:
                _spec = _codebuild.BuildSpec.from_object(_build_inline_spec)
            else:
                _spec = None
            _codebuild.PipelineProject(
                self,
                'project',
                environment=_env,
                encryption_key=_kms.Key.from_key_arn(self, 'DefaultDeploymentAccountKey', key_arn=deployment_region_kms),
                description="ADF CodeBuild Project for {0}".format(map_params['name']),
                project_name="adf-build-{0}".format(map_params['name']),
                timeout=core.Duration.minutes(_timeout),
                build_spec=_spec,
                role=_iam.Role.from_role_arn(self, 'default_build_role', role_arn=_build_role, mutable=False)
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
    def determine_build_image(scope, target, map_params):
        specific_image = None
        if target:
            specific_image = (
                target.get('properties', {}).get('image') or
                map_params['default_providers']['deploy'].get(
                    'properties', {}).get('image')
            )
        else:
            specific_image = (
                map_params['default_providers']['build'].get(
                    'properties', {}).get('image')
            )
        if isinstance(specific_image, dict):
            repo_arn = _ecr.Repository.from_repository_arn(
                scope,
                'custom_repo',
                specific_image.get('repository_arn', ''),
            )
            return _codebuild.LinuxBuildImage.from_ecr_repository(
                repo_arn,
                specific_image.get('tag', 'latest'),
            )
        return getattr(
            _codebuild.LinuxBuildImage,
            (specific_image or DEFAULT_CODEBUILD_IMAGE).upper(),
        )

    @staticmethod
    def generate_build_env_variables(codebuild, shared_modules_bucket, map_params, target=None):
        _output = {
            "PYTHONPATH": codebuild.BuildEnvironmentVariable(value='./adf-build/python'),
            "ADF_PROJECT_NAME": codebuild.BuildEnvironmentVariable(value=map_params['name']),
            "S3_BUCKET_NAME": codebuild.BuildEnvironmentVariable(value=shared_modules_bucket),
            "ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=core.Aws.ACCOUNT_ID)
        }
        _build_env_vars = map_params.get('default_providers', {}).get('build', {}).get('properties', {}).get('environment_variables', {})
        for _env_var in _build_env_vars.items():
            _output[_env_var[0]] = codebuild.BuildEnvironmentVariable(value=str(_env_var[1]))
        if target:
            _target_env_vars = target.get('properties', {}).get('environment_variables', {})
            for _target_env_var in _target_env_vars.items():
                _output[_target_env_var[0]] = codebuild.BuildEnvironmentVariable(value=_target_env_var[1])
            _output["TARGET_NAME"] = codebuild.BuildEnvironmentVariable(value=target['name'])
            _output["TARGET_ACCOUNT_ID"] = codebuild.BuildEnvironmentVariable(value=target['id'])
            _role = map_params['default_providers']['deploy'].get('properties', {}).get('role') or target.get('properties', {}).get('role')
            if _role:
                _output["DEPLOYMENT_ROLE"] = codebuild.BuildEnvironmentVariable(value=_role)
        return _output
