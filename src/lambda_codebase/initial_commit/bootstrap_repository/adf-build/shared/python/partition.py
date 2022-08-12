# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Partition.

A partition is a group of AWS Regions. This module provides a helper function
to help determine the proper partition given a region name. For more details
on partitions, see:
https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html#genref-aws-service-namespaces
"""


def get_partition(region_name: str) -> str:
    """Given the region, this function will return the appropriate partition.

    :param region_name: The name of the region (us-east-1, us-gov-west-1)
    :return: Returns the partition name as a string.
    """

    if region_name.startswith('us-gov'):
        return 'aws-us-gov'

    return 'aws'


def get_organization_api_region(region_name: str) -> str:
    """
    Given the current region, it will determine the partition and use
    that to return the Organizations API region (us-east-1 or us-gov-west-1)

    :param region_name: The name of the region (eu-west-1, us-gov-east-1)
    :return: Returns the AWS Organizations API region to use as a string.
    """
    if get_partition(region_name) == 'aws-us-gov':
        return 'us-gov-west-1'

    return 'us-east-1'
