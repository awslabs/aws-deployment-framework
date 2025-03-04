# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""Tests for partition.py"""

import pytest

from partition import get_partition, IncompatibleRegionError

_us_commercial_regions = [
    'us-east-1',
    'us-west-1',
    'us-west-2'
]

_govcloud_regions = [
    'us-gov-west-1',
    'us-gov-east-1'
]

_china_region = [
    'cn-north-1',
    'cn-northwest-1'
]

_incompatible_regions = [
    'cp-noexist-1'
]

@pytest.mark.parametrize('region', _govcloud_regions)
def test_partition_govcloud_regions(region):
    assert get_partition(region) == 'aws-us-gov'


@pytest.mark.parametrize('region', _us_commercial_regions)
def test_partition_us_commercial_regions(region):
    assert get_partition(region) == 'aws'

@pytest.mark.parametrize('region', _china_region)
def test_partition_china_regions(region):
    assert get_partition(region) == 'aws-cn'

@pytest.mark.parametrize('region', _incompatible_regions)
def test_partition_unknown_regions(region):
    with pytest.raises(IncompatibleRegionError) as excinfo:
        get_partition(region)

    error_message = str(excinfo.value)
    assert error_message.find(f"The region {region} is not supported") >= 0