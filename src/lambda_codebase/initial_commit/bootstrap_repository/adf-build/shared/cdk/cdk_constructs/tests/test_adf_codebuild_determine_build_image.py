# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from copy import deepcopy
from mock import patch
from aws_cdk import (
    aws_codebuild as _codebuild,
    core,
)
from cdk_constructs.adf_codebuild import CodeBuild, DEFAULT_CODEBUILD_IMAGE

SIMPLE_TARGET = {
    'properties': {},
}
SPECIFIC_CODEBUILD_IMAGE_STR = 'STANDARD_3_0'
SPECIFIC_CODEBUILD_IMAGE_ALT_STR = 'STANDARD_2_0'
SPECIFIC_CODEBUILD_IMAGE_ALT2_STR = 'STANDARD_1_0'
SPECIFIC_CODEBUILD_IMAGE_ECR = {
    'repository_arn': 'arn:aws:ecr:region:111111111111:repository/test',
    'tag': 'specific',
}
CODEBUILD_SPECIFIC_MAP_PARAMS_STR = {
    'provider': 'codebuild',
    'properties': {
        'image': SPECIFIC_CODEBUILD_IMAGE_STR,
    }
}
CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR = {
    'provider': 'codebuild',
    'properties': {
        'image': SPECIFIC_CODEBUILD_IMAGE_ALT_STR,
    }
}
CODEBUILD_SPECIFIC_MAP_PARAMS_ALT2_STR = {
    'provider': 'codebuild',
    'properties': {
        'image': SPECIFIC_CODEBUILD_IMAGE_ALT2_STR,
    }
}
CODEBUILD_SPECIFIC_MAP_PARAMS_ECR = {
    'provider': 'codebuild',
    'properties': {
        'image': SPECIFIC_CODEBUILD_IMAGE_ECR,
    }
}

CODEBUILD_BASE_MAP_PARAMS = {
    'default_providers': {
        'build': {},
        'deploy': {},
    },
}


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_build_defaults(ecr_repo, build_image):
    """
    Scenario:
        Target: Not set.
        Build: No specifics, i.e. use defaults.
        Deploy: Specific config set, as str.

    Tests:
        Since the target is not set, it will determine that it is a build
        step. As no specific config for the default build provider is set
        it should return the default config.
    """
    scope = core.Stack()
    target = None
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    # Set deploy one to alternative, so we can test
    # that it is not using this in build steps
    map_params['default_providers']['deploy'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == getattr(
        _codebuild.LinuxBuildImage,
        DEFAULT_CODEBUILD_IMAGE,
    )
    ecr_repo.from_repository_arn.assert_not_called()
    build_image.from_ecr_repository.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_build_str(ecr_repo, build_image):
    """
    Scenario:
        Target: Not set.
        Build: Specific config set, as str, should use this.
        Deploy: Specific config set, as str.

    Tests:
        Since the target is not set, it will determine that it is a build
        step. As specific config for the default build provider is set
        it should use these, not the deploy specific config.
    """
    scope = core.Stack()
    target = None
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_STR
    # Set deploy one to alternative, so we can test
    # that it is not using this in build steps
    map_params['default_providers']['deploy'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == getattr(
        _codebuild.LinuxBuildImage,
        SPECIFIC_CODEBUILD_IMAGE_STR,
    )
    ecr_repo.from_repository_arn.assert_not_called()
    build_image.from_ecr_repository.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_build_ecr(ecr_repo, build_image):
    """
    Scenario:
        Target: Not set.
        Build: Specific config set, as ECR dict, should use this.
        Deploy: Specific config set, as str.

    Tests:
        Since the target is not set, it will determine that it is a build
        step. As specific config for the default build provider is set
        it should use these with ECR, not the deploy specific config.
        Plus setting the 'specific' tag, as that is specified.
    """
    scope = core.Stack()
    target = None
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ECR
    # Set deploy one to alternative, so we can test
    # that it is not using this in build steps
    map_params['default_providers']['deploy'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    from_repo_arn_return_value = {'Some': 'Value'}
    ecr_repo.from_repository_arn.return_value = from_repo_arn_return_value

    from_ecr_repo_return_value = {'Another': 'Object'}
    build_image.from_ecr_repository.return_value = from_ecr_repo_return_value

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == from_ecr_repo_return_value
    ecr_repo.from_repository_arn.assert_called_once_with(
        scope,
        'custom_repo',
        SPECIFIC_CODEBUILD_IMAGE_ECR.get('repository_arn'),
    )
    build_image.from_ecr_repository.assert_called_once_with(
        from_repo_arn_return_value,
        SPECIFIC_CODEBUILD_IMAGE_ECR.get('tag'),
    )


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_build_ecr_no_tag(ecr_repo, build_image):
    """
    Scenario:
        Target: Not set.
        Build: Specific config set, as ECR dict, should use these,
            but has no specific tag set, so should use 'latest'.
        Deploy: Specific config set, as str.

    Tests:
        Since the target is not set, it will determine that it is a build
        step. As specific config for the default build provider is set
        it should use these with ECR, not the deploy specific config.
        Plus setting the 'latest' default tag, as that is not specified.
    """
    scope = core.Stack()
    target = None
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['build'] = deepcopy(
        CODEBUILD_SPECIFIC_MAP_PARAMS_ECR
    )
    del map_params['default_providers']['build']['properties']['image']['tag']
    # Set deploy one to alternative, so we can test
    # that it is not using this in build steps
    map_params['default_providers']['deploy'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    from_repo_arn_return_value = {'Some': 'Value'}
    ecr_repo.from_repository_arn.return_value = from_repo_arn_return_value

    from_ecr_repo_return_value = {'Another': 'Object'}
    build_image.from_ecr_repository.return_value = from_ecr_repo_return_value

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == from_ecr_repo_return_value
    ecr_repo.from_repository_arn.assert_called_once_with(
        scope,
        'custom_repo',
        SPECIFIC_CODEBUILD_IMAGE_ECR.get('repository_arn'),
    )
    build_image.from_ecr_repository.assert_called_once_with(
        from_repo_arn_return_value,
        'latest',
    )


# Deploy mode

@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_deploy_defaults(ecr_repo, build_image):
    """
    Scenario:
        Target: Set, no config.
        Build: Specific config set, as str.
        Build: No specifics, i.e. use defaults.

    Tests:
        Since the target is set, it will determine that it is a deploy
        step. As no specific config for the default deploy provider is set
        it should return the default config.
    """
    scope = core.Stack()
    target = SIMPLE_TARGET
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    # Set build one to alternative, so we can test
    # that it is not using this in deploy steps
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == getattr(
        _codebuild.LinuxBuildImage,
        DEFAULT_CODEBUILD_IMAGE,
    )
    ecr_repo.from_repository_arn.assert_not_called()
    build_image.from_ecr_repository.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_deploy_target_str(ecr_repo, build_image):
    """
    Scenario:
        Target: Specific config set, as str, should use this.
        Build: Specific config set, as str.
        Deploy: No specifics, i.e. would fallback to defaults if no
            target specific config is set.

    Tests:
        Since the target is set, it will determine that it is a deploy
        step. As specific config for the target is set it should use these,
        not the default deploy specific config.
    """
    scope = core.Stack()
    target = CODEBUILD_SPECIFIC_MAP_PARAMS_STR
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    # Set build one to alternative, so we can test
    # that it is not using this in deploy steps
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == getattr(
        _codebuild.LinuxBuildImage,
        SPECIFIC_CODEBUILD_IMAGE_STR,
    )
    ecr_repo.from_repository_arn.assert_not_called()
    build_image.from_ecr_repository.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_deploy_str(ecr_repo, build_image):
    """
    Scenario:
        Target: Set, no specific config.
        Build: Specific config set, as str.
        Deploy: Specific config set, as str, should use this.

    Tests:
        Since the target is set, it will determine that it is a deploy
        step. As specific config for the default deploy provider is set
        it should use these, not the build specific config.
    """
    scope = core.Stack()
    target = SIMPLE_TARGET
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['deploy'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_STR
    # Set build one to alternative, so we can test
    # that it is not using this in deploy steps
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == getattr(
        _codebuild.LinuxBuildImage,
        SPECIFIC_CODEBUILD_IMAGE_STR,
    )
    ecr_repo.from_repository_arn.assert_not_called()
    build_image.from_ecr_repository.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_deploy_target_str_too(ecr_repo, build_image):
    """
    Scenario:
        Target: Specific config set, should use this.
        Build: Specific config set, as str.
        Deploy: Specific config set, as str.

    Tests:
        Since the target is set, it will determine that it is a deploy
        step. As specific config for the target is set it should use these,
        not the default build or deploy specific config.
    """
    scope = core.Stack()
    target = CODEBUILD_SPECIFIC_MAP_PARAMS_ALT2_STR
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['deploy'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_STR
    # Set build one to alternative, so we can test
    # that it is not using this in deploy steps
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == getattr(
        _codebuild.LinuxBuildImage,
        SPECIFIC_CODEBUILD_IMAGE_ALT2_STR,
    )
    ecr_repo.from_repository_arn.assert_not_called()
    build_image.from_ecr_repository.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_deploy_ecr(ecr_repo, build_image):
    """
    Scenario:
        Target: Set, no specific config.
        Build: Specific config set, as str.
        Deploy: Specific config set, as ECR dict, should use this.

    Tests:
        Since the target is set, it will determine that it is a deploy
        step. As specific config for the default deploy provider is set
        it should use these with ECR, not the build specific config.
        Plus setting the 'specific' tag, as that is specified.
    """
    scope = core.Stack()
    target = SIMPLE_TARGET
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['deploy'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ECR
    # Set build one to alternative, so we can test
    # that it is not using this in deploy steps
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    from_repo_arn_return_value = {'Some': 'Value'}
    ecr_repo.from_repository_arn.return_value = from_repo_arn_return_value

    from_ecr_repo_return_value = {'Another': 'Object'}
    build_image.from_ecr_repository.return_value = from_ecr_repo_return_value

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == from_ecr_repo_return_value
    ecr_repo.from_repository_arn.assert_called_once_with(
        scope,
        'custom_repo',
        SPECIFIC_CODEBUILD_IMAGE_ECR.get('repository_arn'),
    )
    build_image.from_ecr_repository.assert_called_once_with(
        from_repo_arn_return_value,
        SPECIFIC_CODEBUILD_IMAGE_ECR.get('tag'),
    )


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_deploy_ecr_too(ecr_repo, build_image):
    """
    Scenario:
        Target: Specific config set, as ECR dict, should use this.
        Build: Specific config set, as str.
        Deploy: Specific config set, as ECR dict.

    Tests:
        Since the target is set, it will determine that it is a deploy
        step. As specific config for the target is set it should use these
        with ECR, not the default build or deploy specific config.
        Plus setting the 'specific' tag, as that is specified.
    """
    scope = core.Stack()
    target = deepcopy(CODEBUILD_SPECIFIC_MAP_PARAMS_ECR)
    target['properties']['image']['repository_arn'] = 'arn:other:one'
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['deploy'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ECR
    # Set build one to alternative, so we can test
    # that it is not using this in deploy steps
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    from_repo_arn_return_value = {'Some': 'Value'}
    ecr_repo.from_repository_arn.return_value = from_repo_arn_return_value

    from_ecr_repo_return_value = {'Another': 'Object'}
    build_image.from_ecr_repository.return_value = from_ecr_repo_return_value

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == from_ecr_repo_return_value
    ecr_repo.from_repository_arn.assert_called_once_with(
        scope,
        'custom_repo',
        target['properties']['image']['repository_arn'],
    )
    build_image.from_ecr_repository.assert_called_once_with(
        from_repo_arn_return_value,
        SPECIFIC_CODEBUILD_IMAGE_ECR.get('tag'),
    )


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_deploy_ecr_no_tag(ecr_repo, build_image):
    """
    Scenario:
        Target: Set, no specific config.
        Build: Specific config set, as str.
        Deploy: Specific config set, as ECR dict, should use these,
            but has no specific tag set, so should use 'latest'.

    Tests:
        Since the target is set, it will determine that it is a deploy
        step. As specific config for the default deploy provider is set
        it should use these with ECR, not the build specific config.
        Plus setting the 'latest' default tag, as that is not specified.
    """
    scope = core.Stack()
    target = SIMPLE_TARGET
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['deploy'] = deepcopy(
        CODEBUILD_SPECIFIC_MAP_PARAMS_ECR
    )
    del map_params['default_providers']['deploy']['properties']['image']['tag']
    # Set build one to alternative, so we can test
    # that it is not using this in deploy steps
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    from_repo_arn_return_value = {'Some': 'Value'}
    ecr_repo.from_repository_arn.return_value = from_repo_arn_return_value

    from_ecr_repo_return_value = {'Another': 'Object'}
    build_image.from_ecr_repository.return_value = from_ecr_repo_return_value

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == from_ecr_repo_return_value
    ecr_repo.from_repository_arn.assert_called_once_with(
        scope,
        'custom_repo',
        SPECIFIC_CODEBUILD_IMAGE_ECR.get('repository_arn'),
    )
    build_image.from_ecr_repository.assert_called_once_with(
        from_repo_arn_return_value,
        'latest',
    )


@patch('cdk_constructs.adf_codebuild._codebuild.LinuxBuildImage')
@patch('cdk_constructs.adf_codebuild._ecr.Repository')
def test_determine_build_image_deploy_ecr_no_tag_too(ecr_repo, build_image):
    """
    Scenario:
        Target: Specific config set, as ECR dict, should use these,
            but has no specific tag set, so should use 'latest'.
        Build: Specific config set, as str.
        Deploy: Specific config set, as ECR dict.

    Tests:
        Since the target is set, it will determine that it is a deploy
        step. As specific config for the target is set it should use these
        with ECR, not the default build or deploy specific config.
        Plus setting the 'latest' default tag, as that is not specified.
    """
    scope = core.Stack()
    target = deepcopy(CODEBUILD_SPECIFIC_MAP_PARAMS_ECR)
    target['properties']['image']['repository_arn'] = 'arn:other:one'
    del target['properties']['image']['tag']
    map_params = deepcopy(CODEBUILD_BASE_MAP_PARAMS)
    map_params['default_providers']['deploy'] = deepcopy(
        CODEBUILD_SPECIFIC_MAP_PARAMS_ECR
    )
    # Set build one to alternative, so we can test
    # that it is not using this in deploy steps
    map_params['default_providers']['build'] = \
        CODEBUILD_SPECIFIC_MAP_PARAMS_ALT_STR

    from_repo_arn_return_value = {'Some': 'Value'}
    ecr_repo.from_repository_arn.return_value = from_repo_arn_return_value

    from_ecr_repo_return_value = {'Another': 'Object'}
    build_image.from_ecr_repository.return_value = from_ecr_repo_return_value

    result = CodeBuild.determine_build_image(
        scope=scope,
        target=target,
        map_params=map_params,
    )

    assert result == from_ecr_repo_return_value
    ecr_repo.from_repository_arn.assert_called_once_with(
        scope,
        'custom_repo',
        target['properties']['image']['repository_arn'],
    )
    build_image.from_ecr_repository.assert_called_once_with(
        from_repo_arn_return_value,
        'latest',
    )
