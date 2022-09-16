"""Tests for partition.py

Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import pytest

from partition import get_partition, IncompatiblePartitionError

_us_commercial_regions = [
    'us-east-1',
    'us-west-1',
    'us-west-2'
]

_govcloud_regions = [
    'us-gov-west-1',
    'us-gov-east-1'
]

_incompatible_regions = [
    'cn-north-1',
    'cn-northwest-1'
]


@pytest.mark.parametrize('region', _govcloud_regions)
def test_partition_govcloud_regions(region):
    assert get_partition(region) == 'aws-us-gov'


@pytest.mark.parametrize('region', _us_commercial_regions)
def test_partition_us_commercial_regions(region):
    assert get_partition(region) == 'aws'


@pytest.mark.parametrize('region', _incompatible_regions)
def test_partition_incompatible_regions(region):
    with pytest.raises(IncompatiblePartitionError) as excinfo:
        get_partition(region)

    error_message = str(excinfo.value)
    assert error_message.find("partition is not supported") >= 0
