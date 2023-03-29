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
    aws_ec2 as _ec2,
    core
)

from cdk_constructs.adf_codepipeline import Action

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
DEFAULT_CODEBUILD_IMAGE = "UBUNTU_14_04_PYTHON_3_7_1"
DEFAULT_BUILD_SPEC_FILENAME = 'buildspec.yml'
DEFAULT_DEPLOY_SPEC_FILENAME = 'deployspec.yml'
ADF_DEFAULT_BUILD_ROLE_NAME = 'adf-codebuild-role'
ADF_DEFAULT_BUILD_TIMEOUT = 20


class CodeBuild(core.Construct):
    # pylint: disable=no-value-for-parameter

    # pylint: disable=W0622
    def __init__(
        self,
        scope: core.Construct,
        id: str,
        shared_modules_bucket: str,
        deployment_region_kms: str,
        deployment_map_source: str,
        deployment_map_name: str,
        map_params: dict,
        target,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)
        stack = core.Stack.of(self)

        # if CodeBuild is being used as a deployment action we want to allow
        # target specific values.
        if target:
            role_name = (
                target
                .get('properties', {})
                .get('role', ADF_DEFAULT_BUILD_ROLE_NAME)
            )
            role_arn = (
                f'arn:{stack.partition}:iam::{ADF_DEPLOYMENT_ACCOUNT_ID}:'
                f'role/{role_name}'
            )
            timeout = (
                target
                .get('properties', {})
                .get('timeout', (
                    map_params['default_providers']['deploy']
                    .get('properties', {})
                    .get('timeout', ADF_DEFAULT_BUILD_TIMEOUT)
                ))
            )
            build_env = _codebuild.BuildEnvironment(
                build_image=CodeBuild.determine_build_image(
                    codebuild_id=id,
                    scope=scope,
                    target=target,
                    map_params=map_params,
                ),
                compute_type=getattr(
                    _codebuild.ComputeType,
                    (
                        target
                        .get('properties', {})
                        .get('size', (
                            map_params['default_providers']['deploy']
                            .get('properties', {})
                            .get('size', "SMALL")
                        ))
                        .upper()
                    ),
                ),
                environment_variables=CodeBuild.generate_build_env_variables(
                    _codebuild,
                    shared_modules_bucket,
                    deployment_map_source,
                    deployment_map_name,
                    map_params,
                    target,
                ),
                privileged=(
                    target
                    .get('properties', {})
                    .get('privileged', (
                        map_params['default_providers']['deploy']
                        .get('properties', {})
                        .get('privileged', False)
                    ))
                ),
            )
            build_spec = CodeBuild.determine_build_spec(
                id,
                (
                    map_params['default_providers']['deploy']
                    .get('properties', {})
                ),
                target,
            )
            self.pipeline_project = _codebuild.PipelineProject(
                self,
                'project',
                environment=build_env,
                encryption_key=_kms.Key.from_key_arn(
                    self,
                    'default_deployment_account_key',
                    key_arn=deployment_region_kms,
                ),
                description=f"ADF CodeBuild Project for {id}",
                project_name=f"adf-deploy-{id}",
                timeout=core.Duration.minutes(timeout),
                role=_iam.Role.from_role_arn(
                    self,
                    'build_role',
                    role_arn=role_arn,
                    mutable=False,
                ),
                build_spec=build_spec,
            )
            self._setup_vpc(
                map_params['default_providers']['deploy'],
                target=target,
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
            role_name = (
                map_params['default_providers']['build']
                .get('properties', {})
                .get('role', ADF_DEFAULT_BUILD_ROLE_NAME)
            )
            role_arn = (
                f'arn:{stack.partition}:iam::{ADF_DEPLOYMENT_ACCOUNT_ID}:'
                f'role/{role_name}'
            )
            timeout = (
                map_params['default_providers']['build']
                .get('properties', {})
                .get('timeout', ADF_DEFAULT_BUILD_TIMEOUT)
            )
            build_env = _codebuild.BuildEnvironment(
                build_image=CodeBuild.determine_build_image(
                    codebuild_id=id,
                    scope=scope,
                    target=target,
                    map_params=map_params
                ),
                compute_type=getattr(
                    _codebuild.ComputeType,
                    (
                        map_params['default_providers']['build']
                        .get('properties', {})
                        .get('size', "SMALL")
                        .upper()
                    ),
                ),
                environment_variables=CodeBuild.generate_build_env_variables(
                    _codebuild,
                    shared_modules_bucket,
                    deployment_map_source,
                    deployment_map_name,
                    map_params,
                ),
                privileged=(
                    map_params['default_providers']['build']
                    .get('properties', {})
                    .get('privileged', False)
                ),
            )
            build_spec = CodeBuild.determine_build_spec(
                id,
                map_params['default_providers']['build'].get('properties', {})
            )
            self.pipeline_project = _codebuild.PipelineProject(
                self,
                'project',
                environment=build_env,
                encryption_key=_kms.Key.from_key_arn(
                    self,
                    'DefaultDeploymentAccountKey',
                    key_arn=deployment_region_kms,
                ),
                description=f"ADF CodeBuild Project for {map_params['name']}",
                project_name=f"adf-build-{map_params['name']}",
                timeout=core.Duration.minutes(timeout),
                build_spec=build_spec,
                role=_iam.Role.from_role_arn(
                    self,
                    'default_build_role',
                    role_arn=role_arn,
                    mutable=False,
                ),
            )
            self._setup_vpc(map_params['default_providers']['build'])
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

    def _setup_vpc(self, default_provider, target=None):
        default_props = default_provider.get('properties', {})
        # This will either be empty (build stage) or configured (deploy stage)
        target_props = (target or {}).get('properties', {})
        vpc_id = target_props.get('vpc_id', default_props.get('vpc_id'))
        subnet_ids = target_props.get(
            'subnet_ids',
            default_props.get('subnet_ids', []),
        )
        security_group_ids = target_props.get(
            'security_group_ids',
            default_props.get('security_group_ids', []),
        )
        if vpc_id:
            if not subnet_ids:
                raise Exception(
                    "CodeBuild environment of "
                    f"{self.pipeline_project.project_name} has a "
                    f"VPC Id ({vpc_id}) set, but no subnets are configured. "
                    "When specifying the VPC Id for a given CodeBuild "
                    "environment, you also need to specify the subnet_ids "
                    "and optionally the security_group_ids that should be "
                    "used by the CodeBuild instance."
                )
            if not security_group_ids:
                default_security_group = _ec2.CfnSecurityGroup(
                    self,
                    'sg',
                    group_description=(
                        f"The default security group for {self.node.id}"
                    ),
                    security_group_egress=[
                        {
                            "cidrIp": "0.0.0.0/0",
                            "ipProtocol": "-1",
                        }
                    ],
                    vpc_id=vpc_id,
                )
                security_group_ids = [
                    default_security_group.get_att("GroupId"),
                ]
            self.pipeline_project.node.default_child.add_property_override(
                "VpcConfig",
                {
                    "VpcId": vpc_id,
                    "Subnets": subnet_ids,
                    "SecurityGroupIds": security_group_ids,
                },
            )
        elif subnet_ids or security_group_ids:
            raise Exception(
                "CodeBuild environment of "
                f"{self.pipeline_project.project_name} requires a VPC Id when "
                "configured to connect to specific subnets."
            )

    @staticmethod
    def _determine_stage_build_spec(
        codebuild_id,
        props,
        stage_name,
        default_filename,
    ):
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
            if (
                'spec_inline' in target_props
                or 'spec_filename' in target_props
            ):
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
        image_name = (
            (
                specific_image
                or DEFAULT_CODEBUILD_IMAGE
            ).upper()
        )
        if hasattr(_codebuild.LinuxBuildImage, image_name):
            return getattr(_codebuild.LinuxBuildImage, image_name)
        if specific_image.startswith('docker-hub://'):
            specific_image = specific_image.split('docker-hub://')[-1]
            return _codebuild.LinuxBuildImage.from_docker_registry(
                specific_image,
            )
        raise Exception(
            f"The CodeBuild image {specific_image} could not be found."
        )

    @staticmethod
    def determine_build_image(codebuild_id, scope, target, map_params):
        specific_image = None
        if target:
            specific_image = (
                target.get('properties', {}).get('image')
                or (
                    map_params['default_providers']['deploy']
                    .get('properties', {})
                    .get('image')
                )
            )
        else:
            specific_image = (
                map_params['default_providers']['build']
                .get('properties', {})
                .get('image')
            )
        if isinstance(specific_image, dict):
            response_specific_image = specific_image['repository_arn']
            # We just use the ecr repo name and construct the ECR ARN
            if not response_specific_image.startswith('arn:aws:ecr:'):
                constructed_repository_arn = f"arn:aws:ecr:{ADF_DEPLOYMENT_REGION}:{ADF_DEPLOYMENT_ACCOUNT_ID}:{response_specific_image}"
                repo_arn = _ecr.Repository.from_repository_arn(
                    scope,
                    f'custom_repo_{codebuild_id}',
                    constructed_repository_arn
                )
                return _codebuild.LinuxBuildImage.from_ecr_repository(
                    repo_arn,
                    specific_image.get('tag', 'latest'),
                )
            # We take the full ECR Arn - Default Behaviour
            repo_arn = _ecr.Repository.from_repository_arn(
                scope,
                f'custom_repo_{codebuild_id}',
                specific_image.get('repository_arn', ''),
            )
            return _codebuild.LinuxBuildImage.from_ecr_repository(
                repo_arn,
                specific_image.get('tag', 'latest'),
            )
        return CodeBuild.get_image_by_name(specific_image)

    @staticmethod
    def generate_build_env_variables(
        codebuild,
        shared_modules_bucket,
        deployment_map_source,
        deployment_map_name,
        map_params,
        target=None,
    ):
        build_env_vars = {
            "PYTHONPATH": "./adf-build/python",
            "ADF_PROJECT_NAME": map_params['name'],
            "ADF_DEPLOYMENT_MAP_SOURCE": deployment_map_source,
            "ADF_DEPLOYMENT_MAP_NAME": deployment_map_name,
            "S3_BUCKET_NAME": shared_modules_bucket,
            "ACCOUNT_ID": core.Aws.ACCOUNT_ID,
            **(
                map_params
                .get('default_providers', {})
                .get(
                    (
                        'deploy'
                        if target
                        else 'build'
                    ),
                    {},
                )
                .get('properties', {})
                .get('environment_variables', {})
            ),
            **(
                # Target should go second, as this overwrites any
                # existing key/value, so it overrides the defaults
                (
                    target or {}
                )
                .get('properties', {})
                .get('environment_variables', {})
            )
        }

        if target:
            build_env_vars['TARGET_NAME'] = target['name']
            build_env_vars["TARGET_ACCOUNT_ID"] = target['id']
            deploy_role_name = (
                target
                .get('properties', {})
                .get('role', (
                    map_params['default_providers']['deploy']
                    .get('properties', {})
                    .get('role')
                ))
            )
            if deploy_role_name:
                build_env_vars["DEPLOYMENT_ROLE"] = deploy_role_name

        return {
            key: codebuild.BuildEnvironmentVariable(value=value)
            for key, value in build_env_vars.items()
        }
