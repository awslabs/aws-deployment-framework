# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import botocore
from botocore.stub import Stubber
from pytest import fixture, raises
from mock import Mock, patch, mock_open
from s3 import S3


@fixture
def us_east_1_cls():
    return S3(
        'us-east-1',
        'some_bucket'
    )


@fixture
def eu_west_1_cls():
    cls = S3(
        'eu-west-1',
        'some_bucket'
    )
    return cls


def test_supported_path_styles_path():
    assert 'path' in S3.supported_path_styles()


def test_supported_path_styles_s3_key_only():
    assert 's3-key-only' in S3.supported_path_styles()


def test_supported_path_styles_s3_uri():
    assert 's3-uri' in S3.supported_path_styles()


def test_supported_path_styles_s3_url():
    assert 's3-url' in S3.supported_path_styles()


def test_supported_path_styles_virtual_hosted():
    assert 'virtual-hosted' in S3.supported_path_styles()


def test_build_pathing_style_s3_url_us_east_1(us_east_1_cls):
    key = 'some/key'
    assert us_east_1_cls.build_pathing_style('s3-url', key) == \
        "s3://{bucket}/{key}".format(
            bucket=us_east_1_cls.bucket,
            key=key,
        )


def test_build_pathing_style_s3_url_any_other_region(eu_west_1_cls):
    key = 'some/key'
    assert eu_west_1_cls.build_pathing_style('s3-url', key) == \
        "s3://{bucket}/{key}".format(
            bucket=eu_west_1_cls.bucket,
            key=key,
        )


def test_build_pathing_style_s3_uri_us_east_1(us_east_1_cls):
    key = 'some/key'
    assert us_east_1_cls.build_pathing_style('s3-uri', key) == \
        "{bucket}/{key}".format(
            bucket=us_east_1_cls.bucket,
            key=key,
        )


def test_build_pathing_style_s3_uri_any_other_region(eu_west_1_cls):
    key = 'some/key'
    assert eu_west_1_cls.build_pathing_style('s3-uri', key) == \
        "{bucket}/{key}".format(
            bucket=eu_west_1_cls.bucket,
            key=key,
        )


def test_build_pathing_style_s3_key_only_us_east_1(us_east_1_cls):
    key = 'some/key'
    assert us_east_1_cls.build_pathing_style('s3-key-only', key) == \
        "{key}".format(
            key=key,
        )


def test_build_pathing_style_s3_key_only_any_other_region(eu_west_1_cls):
    key = 'some/key'
    assert eu_west_1_cls.build_pathing_style('s3-key-only', key) == \
        "{key}".format(
            key=key,
        )


def test_build_pathing_style_path_us_east_1(us_east_1_cls):
    key = 'some/key'
    assert us_east_1_cls.build_pathing_style('path', key) == \
        "https://s3.amazonaws.com/{bucket}/{key}".format(
            bucket=us_east_1_cls.bucket,
            key=key,
        )


def test_build_pathing_style_path_any_other_region(eu_west_1_cls):
    key = 'some/key'
    assert eu_west_1_cls.build_pathing_style('path', key) == \
        "https://s3-{region}.amazonaws.com/{bucket}/{key}".format(
            region=eu_west_1_cls.region,
            bucket=eu_west_1_cls.bucket,
            key=key,
        )


def test_build_pathing_style_virtual_hosted_us_east_1(us_east_1_cls):
    key = 'some/key'
    assert us_east_1_cls.build_pathing_style('virtual-hosted', key) == \
        "https://{bucket}.s3.amazonaws.com/{key}".format(
            bucket=us_east_1_cls.bucket,
            key=key,
        )


def test_build_pathing_style_virtual_hosted_any_other_region(eu_west_1_cls):
    key = 'some/key'
    assert eu_west_1_cls.build_pathing_style('virtual-hosted', key) == \
        "https://{bucket}.s3-{region}.amazonaws.com/{key}".format(
            region=eu_west_1_cls.region,
            bucket=eu_west_1_cls.bucket,
            key=key,
        )


def test_build_pathing_style_unknown_style(us_east_1_cls):
    key = 'some/key'
    style = 'unknown'
    correct_error_message = (
        "Unknown upload style syntax: {style}. "
        "Valid options include: s3-uri, path, or virtual-hosted."
    ).format(style=style)
    with raises(Exception) as excinfo:
        us_east_1_cls.build_pathing_style(style, key)

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0


@patch('s3.S3.build_pathing_style')
@patch('s3.S3._perform_put_object')
@patch('s3.S3._does_object_exist')
def test_put_object_no_checks_always_upload(does_exist, perform_put,
                                            build_path, eu_west_1_cls):
    object_key = "some"
    object_path = "s3://bucket/{key}".format(key=object_key)
    file_path = "some_imaginary_file.json"
    path_style = "s3-url"
    does_exist.return_value = True
    build_path.return_value = object_path

    return_value = eu_west_1_cls.put_object(
        key=object_key,
        file_path=file_path,
        style=path_style,
        pre_check=False,
    )

    assert return_value == object_path

    does_exist.assert_not_called()
    perform_put.assert_called_once_with(object_key, file_path)
    build_path.assert_called_once_with(path_style, object_key)


@patch('s3.S3.build_pathing_style')
@patch('s3.S3._perform_put_object')
@patch('s3.S3._does_object_exist')
def test_put_object_do_check_upload_when_missing(
        does_exist, perform_put, build_path, eu_west_1_cls):
    object_key = "some"
    object_path = "s3://bucket/{key}".format(key=object_key)
    file_path = "some_imaginary_file.json"
    path_style = "s3-url"
    does_exist.return_value = False
    build_path.return_value = object_path

    return_value = eu_west_1_cls.put_object(
        key=object_key,
        file_path=file_path,
        style=path_style,
        pre_check=True,
    )

    assert return_value == object_path

    does_exist.assert_called_once_with(object_key)
    perform_put.assert_called_once_with(object_key, file_path)
    build_path.assert_called_once_with(path_style, object_key)


@patch('s3.S3.build_pathing_style')
@patch('s3.S3._perform_put_object')
@patch('s3.S3._does_object_exist')
def test_put_object_do_check_no_upload_object_present(
        does_exist, perform_put, build_path, eu_west_1_cls):
    object_key = "some"
    object_path = "s3://bucket/{key}".format(key=object_key)
    file_path = "some_imaginary_file.json"
    path_style = "s3-url"
    does_exist.return_value = True
    build_path.return_value = object_path

    return_value = eu_west_1_cls.put_object(
        key=object_key,
        file_path=file_path,
        style=path_style,
        pre_check=True,
    )

    assert return_value == object_path

    does_exist.assert_called_once_with(object_key)
    perform_put.assert_not_called()
    build_path.assert_called_once_with(path_style, object_key)


@patch('s3.boto3.client')
def test_does_object_exist_yes(boto3_client):
    s3_client = botocore.session.get_session().create_client('s3')
    s3_client_stubber = Stubber(s3_client)
    boto3_client.return_value = s3_client
    object_key = "some"

    s3_cls = S3(
        'eu-west-1',
        'some_bucket'
    )
    response = {}
    expected_params = {
        'Bucket': s3_cls.bucket,
        'Key': object_key,
    }
    s3_client_stubber.add_response('get_object', response, expected_params)
    s3_client_stubber.activate()

    assert s3_cls._does_object_exist(key=object_key)

    boto3_client.assert_called_once_with('s3', region_name='eu-west-1')
    s3_client_stubber.assert_no_pending_responses()


@patch('s3.boto3.client')
def test_does_object_exist_no(boto3_client):
    s3_client = botocore.session.get_session().create_client('s3')
    s3_client_stubber = Stubber(s3_client)
    boto3_client.return_value = s3_client
    object_key = "some"

    s3_cls = S3(
        'eu-west-1',
        'some_bucket'
    )
    s3_client_stubber.add_client_error(
        'get_object',
        expected_params={'Bucket': s3_cls.bucket, 'Key': object_key},
        http_status_code=404,
        service_error_code='NoSuchKey',
    )
    s3_client_stubber.activate()

    assert not s3_cls._does_object_exist(key=object_key)

    boto3_client.assert_called_once_with('s3', region_name='eu-west-1')
    s3_client_stubber.assert_no_pending_responses()


@patch('s3.boto3.resource')
@patch('s3.LOGGER')
def test_perform_put_object_success(logger, boto3_resource):
    s3_resource = Mock()
    s3_object = Mock()
    s3_resource.Object.return_value = s3_object
    boto3_resource.return_value = s3_resource
    object_key = "some"
    file_path = "some-file.json"
    file_data = 'some file data'

    s3_cls = S3(
        'eu-west-1',
        'some_bucket'
    )
    with patch("builtins.open", mock_open(read_data=file_data)) as mock_file:
        s3_cls._perform_put_object(
            key=object_key,
            file_path=file_path,
        )
        mock_file.assert_called_with(file_path, mode='rb')
        s3_resource.Object.assert_called_once_with(s3_cls.bucket, object_key)
        s3_object.put.assert_called_once_with(Body=mock_file.return_value)

    logger.info.assert_called_once_with(
        "Uploading %s as %s to S3 Bucket %s in %s",
        file_path,
        object_key,
        s3_cls.bucket,
        s3_cls.region,
    )
    logger.debug.assert_called_once_with(
        "Upload of %s was successful.",
        object_key,
    )
    logger.error.assert_not_called()
    boto3_resource.assert_called_with('s3', region_name='eu-west-1')


@patch('s3.boto3.resource')
@patch('s3.LOGGER')
def test_perform_put_object_no_such_file(logger, boto3_resource):
    s3_resource = Mock()
    s3_object = Mock()
    s3_resource.Object.return_value = s3_object
    boto3_resource.return_value = s3_resource
    object_key = "some"
    file_path = "some-file.json"

    s3_cls = S3(
        'eu-west-1',
        'some_bucket'
    )
    correct_error_message = "File not found exception"
    with patch("builtins.open") as mock_file:
        mock_file.side_effect = Exception(correct_error_message)
        with raises(Exception) as excinfo:
            s3_cls._perform_put_object(
                key=object_key,
                file_path=file_path,
            )

        error_message = str(excinfo.value)
        assert error_message.find(correct_error_message) >= 0

        mock_file.assert_called_with(file_path, mode='rb')
        s3_resource.Object.assert_not_called()
        s3_object.put.assert_not_called()

    logger.info.assert_called_once_with(
        "Uploading %s as %s to S3 Bucket %s in %s",
        file_path,
        object_key,
        s3_cls.bucket,
        s3_cls.region,
    )
    logger.debug.assert_not_called()
    logger.error.assert_called_once_with(
        "Failed to upload %s",
        object_key,
        exc_info=True,
    )
    boto3_resource.assert_called_with('s3', region_name='eu-west-1')


@patch('s3.boto3.resource')
@patch('s3.LOGGER')
def test_perform_put_object_failed(logger, boto3_resource):
    s3_resource = Mock()
    s3_object = Mock()
    s3_resource.Object.return_value = s3_object
    boto3_resource.return_value = s3_resource
    object_key = "some"
    file_path = "some-file.json"
    file_data = 'some file data'

    s3_cls = S3(
        'eu-west-1',
        'some_bucket'
    )
    correct_error_message = "Test exception"
    s3_object.put.side_effect = Exception(correct_error_message)
    with patch("builtins.open", mock_open(read_data=file_data)) as mock_file:
        with raises(Exception) as excinfo:
            s3_cls._perform_put_object(
                key=object_key,
                file_path=file_path,
            )

        error_message = str(excinfo.value)
        assert error_message.find(correct_error_message) >= 0

        mock_file.assert_called_with(file_path, mode='rb')
        s3_resource.Object.assert_called_once_with(s3_cls.bucket, object_key)
        s3_object.put.assert_called_once_with(Body=mock_file.return_value)

    logger.info.assert_called_once_with(
        "Uploading %s as %s to S3 Bucket %s in %s",
        file_path,
        object_key,
        s3_cls.bucket,
        s3_cls.region,
    )
    logger.debug.assert_not_called()
    logger.error.assert_called_once_with(
        "Failed to upload %s",
        object_key,
        exc_info=True,
    )
    boto3_resource.assert_called_with('s3', region_name='eu-west-1')
