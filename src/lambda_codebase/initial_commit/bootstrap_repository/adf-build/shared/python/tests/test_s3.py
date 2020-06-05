# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from pytest import fixture, raises
from stubs import stub_s3
from mock import Mock
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
