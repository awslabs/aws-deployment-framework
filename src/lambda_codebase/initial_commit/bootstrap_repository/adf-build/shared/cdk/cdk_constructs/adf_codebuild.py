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
DEFAULT_BUILD_SPEC_FILENAME = 'buildspec.yml'
DEFAULT_DEPLOY_SPEC_FILENAME = 'deployspec.yml'


class CodeBuild(core.Construct):
    # pylint: disable=no-value-for-parameter

    def __init__(self, scope: core.Construct, id: str, shared_modules_bucket: str, deployment_region_kms: str, map_params: dict, target, **kwargs): #pylint: disable=W0622
        super().__init__(scope, id, **kwargs)
        stack = core.Stack.of(self)

        ADF_DEFAULT_BUILD_ROLE = f'arn:{stack.partition}:iam::{ADF_DEPLOYMENT_ACCOUNT_ID}:role/adf-codebuild-role'
        ADF_DEFAULT_BUILD_TIMEOUT = 20

        # if CodeBuild is being used as a deployment action we want to allow target specific values.
        if target:
            _role_name = target.get('properties', {}).get('role')
            _build_role = f'arn:{stack.partition}:iam::{ADF_DEPLOYMENT_ACCOUNT_ID}:role/{_role_name}' if _role_name else ADF_DEFAULT_BUILD_ROLE
            _timeout = target.get('properties', {}).get('timeout') or map_params['default_providers']['deploy'].get('properties', {}).get('timeout') or ADF_DEFAULT_BUILD_TIMEOUT
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
            build_spec = CodeBuild.determine_build_spec(
                id,
                map_params['default_providers']['deploy'].get('properties', {}),
                target,
            )
            _codebuild.PipelineProject(
                self,
                'project',
                environment=_env,
                encryption_key=_kms.Key.from_key_arn(self, 'default_deployment_account_key', key_arn=deployment_region_kms),
                description=f"ADF CodeBuild Project for {id}",
                project_name=f"adf-deploy-{id}",
                timeout=core.Duration.minutes(_timeout),
                role=_iam.Role.from_role_arn(self, 'build_role', role_arn=_build_role, mutable=False),
                build_spec=build_spec,
            )
            self.deploy = Action(
                name=id,
                provider="CodeBuild",
                category="Build",
                project_name=f"adf-deploy-{id}",
                run_order=1,
                target=target,
                map_params=map_params,
                action_name=id,
            ).config
        else:
            _role_name = map_params['default_providers']['build'].get(
                'properties', {}).get('role')
            _build_role = f'arn:{stack.partition}:iam::{ADF_DEPLOYMENT_ACCOUNT_ID}:role/{_role_name}' if _role_name else ADF_DEFAULT_BUILD_ROLE
            _timeout = map_params['default_providers']['build'].get('properties', {}).get('timeout') or ADF_DEFAULT_BUILD_TIMEOUT
            _env = _codebuild.BuildEnvironment(
                build_image=CodeBuild.determine_build_image(scope, target, map_params),
                compute_type=getattr(_codebuild.ComputeType, map_params['default_providers']['build'].get('properties', {}).get('size', "SMALL").upper()),
                environment_variables=CodeBuild.generate_build_env_variables(_codebuild, shared_modules_bucket, map_params),
                privileged=map_params['default_providers']['build'].get('properties', {}).get('privileged', False)
            )
            if _role_name:
                ADF_DEFAULT_BUILD_ROLE = f'arn:{stack.partition}:iam::{ADF_DEPLOYMENT_ACCOUNT_ID}:role/{_role_name}'
            build_spec = CodeBuild.determine_build_spec(
                id,
                map_params['default_providers']['build'].get('properties', {})
            )
            _codebuild.PipelineProject(
                self,
                'project',
                environment=_env,
                encryption_key=_kms.Key.from_key_arn(self, 'DefaultDeploymentAccountKey', key_arn=deployment_region_kms),
                description=f"ADF CodeBuild Project for {map_params['name']}",
                project_name=f"adf-build-{map_params['name']}",
                timeout=core.Duration.minutes(_timeout),
                build_spec=build_spec,
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
    def _determine_stage_build_spec(codebuild_id, props, stage_name, default_filename):
        filename = props.get('spec_filename')
        spec_inline = props.get('spec_inline', {})
        if filename and spec_inline:
            raise Exception(
                "The spec_filename and spec_inline are both present "
                f"inside the {stage_name} stage definition of {codebuild_id}. "
                "Whereas only one of these two is allowed."
            )

        if spec_inline:
            return _codebuild.BuildSpec.from_object(spec_inline)

        return _codebuild.BuildSpec.from_source_filename(
            filename or default_filename,
        )

    @staticmethod
    def determine_build_spec(codebuild_id, default_props, target=None):
        if target:
            target_props = target.get('properties', {})
            if 'spec_inline' in target_props or 'spec_filename' in target_props:
                return CodeBuild._determine_stage_build_spec(
                    codebuild_id=codebuild_id,
                    props=target_props,
                    stage_name='deploy target',
                    default_filename=DEFAULT_DEPLOY_SPEC_FILENAME,
                )
        stage_type = 'deploy' if target else 'build'
        return CodeBuild._determine_stage_build_spec(
            codebuild_id=codebuild_id,
            props=default_props,
            stage_name=f'default {stage_type}',
            default_filename=(
                DEFAULT_DEPLOY_SPEC_FILENAME
                if target
                else DEFAULT_BUILD_SPEC_FILENAME
            ),
        )

    @staticmethod
    def get_image_by_name(specific_image: str):
        if hasattr(_codebuild.LinuxBuildImage,
            (specific_image or DEFAULT_CODEBUILD_IMAGE).upper()):
            return getattr(_codebuild.LinuxBuildImage,
                (specific_image or DEFAULT_CODEBUILD_IMAGE).upper())
        if specific_image.startswith('docker-hub://'):
            specific_image = specific_image.split('docker-hub://')[-1]
            return _codebuild.LinuxBuildImage.from_docker_registry(specific_image)
        raise Exception(
            f"The CodeBuild image {specific_image} could not be found."
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
        return CodeBuild.get_image_by_name(specific_image)

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
            _deploy_env_vars = map_params.get('default_providers', {}).get('deploy', {}).get('properties', {}).get('environment_variables', {})
            for _env_var in _deploy_env_vars.items():
                _output[_env_var[0]] = codebuild.BuildEnvironmentVariable(value=str(_env_var[1]))

            _target_env_vars = target.get('properties', {}).get('environment_variables', {})
            for _target_env_var in _target_env_vars.items():
                _output[_target_env_var[0]] = codebuild.BuildEnvironmentVariable(value=_target_env_var[1])
            _output["TARGET_NAME"] = codebuild.BuildEnvironmentVariable(value=target['name'])
            _output["TARGET_ACCOUNT_ID"] = codebuild.BuildEnvironmentVariable(value=target['id'])
            _role = map_params['default_providers']['deploy'].get('properties', {}).get('role') or target.get('properties', {}).get('role')
            if _role:
                _output["DEPLOYMENT_ROLE"] = codebuild.BuildEnvironmentVariable(value=_role)
        return _output
