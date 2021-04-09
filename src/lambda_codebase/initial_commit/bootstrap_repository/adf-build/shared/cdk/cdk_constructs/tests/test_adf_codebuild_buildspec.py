# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import pytest
from mock import patch
from cdk_constructs.adf_codebuild import CodeBuild, DEFAULT_BUILD_SPEC_FILENAME, DEFAULT_DEPLOY_SPEC_FILENAME


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_file_and_inline_specified_no_target(buildspec_mock):
    codebuild_id = 'some-id'
    spec_inline = {
        'Some-Object': 'Some-Value',
    }
    spec_filename = 'some-file-name.yml'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'
    correct_error_message = (
        "The spec_filename and spec_inline are both present "
        "inside the default build stage definition of {0}. "
        "Whereas only one of these two is allowed.".format(codebuild_id)
    )

    with pytest.raises(Exception) as excinfo:
        CodeBuild.determine_build_spec(
            codebuild_id=codebuild_id,
            default_props={
                'spec_filename': spec_filename,
                'spec_inline': spec_inline,
            },
        )


    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    buildspec_mock.from_object.assert_not_called()
    buildspec_mock.from_source_filename.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_file_and_inline_specified_in_target(buildspec_mock):
    codebuild_id = 'some-id'
    spec_inline = {
        'Some-Object': 'Some-Value',
    }
    spec_filename = 'some-file-name.yml'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'
    correct_error_message = (
        "The spec_filename and spec_inline are both present "
        "inside the deploy target stage definition of {0}. "
        "Whereas only one of these two is allowed.".format(codebuild_id)
    )

    with pytest.raises(Exception) as excinfo:
        CodeBuild.determine_build_spec(
            codebuild_id=codebuild_id,
            default_props={},
            target={
                'properties': {
                    'spec_filename': spec_filename,
                    'spec_inline': spec_inline,
                },
            },
        )


    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    buildspec_mock.from_object.assert_not_called()
    buildspec_mock.from_source_filename.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_file_and_inline_specified_in_deploy(buildspec_mock):
    codebuild_id = 'some-id'
    spec_inline = {
        'Some-Object': 'Some-Value',
    }
    spec_filename = 'some-file-name.yml'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'
    correct_error_message = (
        "The spec_filename and spec_inline are both present "
        "inside the default deploy stage definition of {0}. "
        "Whereas only one of these two is allowed.".format(codebuild_id)
    )

    with pytest.raises(Exception) as excinfo:
        CodeBuild.determine_build_spec(
            codebuild_id=codebuild_id,
            default_props={
                'spec_filename': spec_filename,
                'spec_inline': spec_inline,
            },
            target={
                'properties': {},
            }
        )


    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0

    buildspec_mock.from_object.assert_not_called()
    buildspec_mock.from_source_filename.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_inline_specified_no_target(buildspec_mock):
    codebuild_id = 'some-id'
    spec_inline = {
        'Some-Object': 'Some-Value',
    }
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'

    return_value = CodeBuild.determine_build_spec(
        codebuild_id=codebuild_id,
        default_props={
            'spec_inline': spec_inline,
        },
    )

    assert return_value == buildspec_mock.from_object.return_value
    buildspec_mock.from_object.assert_called_once_with(spec_inline)
    buildspec_mock.from_source_filename.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_inline_specified_in_target(buildspec_mock):
    codebuild_id = 'some-id'
    spec_inline = {
        'Some-Object': 'Some-Value',
    }
    spec_filename = 'some-file-name.yml'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'

    return_value = CodeBuild.determine_build_spec(
        codebuild_id=codebuild_id,
        default_props={
            'spec_filename': spec_filename,
        },
        target={
            'properties': {
                'spec_inline': spec_inline,
            },
        },
    )

    assert return_value == buildspec_mock.from_object.return_value
    buildspec_mock.from_object.assert_called_once_with(spec_inline)
    buildspec_mock.from_source_filename.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_inline_specified_in_deploy(buildspec_mock):
    codebuild_id = 'some-id'
    spec_inline = {
        'Some-Object': 'Some-Value',
    }
    spec_filename = 'some-file-name.yml'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'

    return_value = CodeBuild.determine_build_spec(
        codebuild_id=codebuild_id,
        default_props={
            'spec_inline': spec_inline,
        },
        target={
            'properties': {},
        },
    )

    assert return_value == buildspec_mock.from_object.return_value
    buildspec_mock.from_object.assert_called_once_with(spec_inline)
    buildspec_mock.from_source_filename.assert_not_called()


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_filename_specified_no_target(buildspec_mock):
    codebuild_id = 'some-id'
    spec_filename = 'some-file-name.yml'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'

    return_value = CodeBuild.determine_build_spec(
        codebuild_id=codebuild_id,
        default_props={
            'spec_filename': spec_filename,
        },
    )

    assert return_value == buildspec_mock.from_source_filename.return_value
    buildspec_mock.from_object.assert_not_called()
    buildspec_mock.from_source_filename.assert_called_once_with(spec_filename)


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_filename_specified_in_target(buildspec_mock):
    codebuild_id = 'some-id'
    spec_inline = {
        'Some-Object': 'Some-Value',
    }
    spec_filename = 'some-file-name.yml'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'

    return_value = CodeBuild.determine_build_spec(
        codebuild_id=codebuild_id,
        default_props={
            'spec_inline': spec_inline,
        },
        target={
            'properties': {
                'spec_filename': spec_filename,
            },
        },
    )

    assert return_value == buildspec_mock.from_source_filename.return_value
    buildspec_mock.from_object.assert_not_called()
    buildspec_mock.from_source_filename.assert_called_once_with(spec_filename)


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_filename_specified_in_deploy(buildspec_mock):
    codebuild_id = 'some-id'
    spec_inline = {
        'Some-Object': 'Some-Value',
    }
    spec_filename = 'some-file-name.yml'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'

    return_value = CodeBuild.determine_build_spec(
        codebuild_id=codebuild_id,
        default_props={
            'spec_filename': spec_filename,
        },
        target={
            'properties': {},
        },
    )

    assert return_value == buildspec_mock.from_source_filename.return_value
    buildspec_mock.from_object.assert_not_called()
    buildspec_mock.from_source_filename.assert_called_once_with(spec_filename)


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_no_spec_no_target(buildspec_mock):
    codebuild_id = 'some-id'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'

    return_value = CodeBuild.determine_build_spec(
        codebuild_id=codebuild_id,
        default_props={},
    )

    assert return_value == buildspec_mock.from_source_filename.return_value
    buildspec_mock.from_object.assert_not_called()
    buildspec_mock.from_source_filename.assert_called_once_with(
        DEFAULT_BUILD_SPEC_FILENAME,
    )


@patch('cdk_constructs.adf_codebuild._codebuild.BuildSpec')
def test_determine_build_spec_with_no_spec_in_target_and_deploy(buildspec_mock):
    codebuild_id = 'some-id'
    buildspec_mock.from_object.return_value = 'From-Object'
    buildspec_mock.from_source_filename.return_value = 'From-Source'

    return_value = CodeBuild.determine_build_spec(
        codebuild_id=codebuild_id,
        default_props={},
        target={
            'properties': {},
        },
    )

    assert return_value == buildspec_mock.from_source_filename.return_value
    buildspec_mock.from_object.assert_not_called()
    buildspec_mock.from_source_filename.assert_called_once_with(
        DEFAULT_DEPLOY_SPEC_FILENAME,
    )
