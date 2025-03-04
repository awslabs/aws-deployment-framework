# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""Partition.

A partition is a group of AWS Regions. This module provides a helper function
to help determine the proper partition given a region name. For more details
on partitions, see:
https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html#genref-aws-service-namespaces
"""

from boto3.session import Session
from botocore.exceptions import UnknownRegionError

class IncompatibleRegionError(Exception):
    """Raised in case the regions is not supported."""
    pass

def get_partition(region_name: str) -> str:
    """Given the region, this function will return the appropriate partition.

    :param region_name: The name of the region (us-east-1, us-gov-west-1, cn-north-1)
    :raises IncompatibleRegionError: If the provided region is not supported.
    :return: Returns the partition name as a string.
    """
    try:
        partition = Session().get_partition_for_region(region_name)
    except UnknownRegionError as e:
        raise IncompatibleRegionError(
            f'The region {region_name} is not supported.'
        )
    return partition

def get_organization_api_region(region_name: str) -> str:
    """
    Given the current region, it will determine the partition and use
    that to return the Organizations API region (us-east-1 or us-gov-west-1 or cn-northwest-1)

    :param region_name: The name of the region (eu-west-1, us-gov-east-1 or cn-northwest-1)
    :return: Returns the AWS Organizations API region to use as a string.
    """
    if get_partition(region_name) == 'aws-us-gov':
        return 'us-gov-west-1'
    elif get_partition(region_name) == 'aws-cn':
        return 'cn-northwest-1'
    return 'us-east-1'

def get_aws_domain(region_name: str) -> str:
    """
    Get AWS domain suffix
    """
    if region_name.startswith("cn-north"):
        return "amazonaws.com.{0}".format(region_name.split("-")[0])
    else:
        return "amazonaws.com"