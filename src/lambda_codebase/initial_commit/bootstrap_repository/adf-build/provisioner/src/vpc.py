# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Remove default VPC and related resources
"""
from time import sleep
from botocore import exceptions
from logger import configure_logger
LOGGER = configure_logger(__name__)


def vpc_cleanup(account_id, vpcid, role, region):
    if not vpcid:
        return
    try:
        ec2 = role.resource('ec2', region_name=region)
        ec2client = ec2.meta.client
        vpc = ec2.Vpc(vpcid)
        # Detach and delete all gateways associated with the VPC
        for gateway in vpc.internet_gateways.all():
            vpc.detach_internet_gateway(InternetGatewayId=gateway.id)
            gateway.delete()
        # Route table associations
        for route_table in vpc.route_tables.all():
            for rt_association in route_table.associations:
                if not rt_association.main:
                    rt_association.delete()
        # Security Group
        for security_group in vpc.security_groups.all():
            if security_group.group_name != 'default':
                security_group.delete()
        # Network interfaces
        for subnet in vpc.subnets.all():
            for interface in subnet.network_interfaces.all():
                interface.delete()
            subnet.delete()
        # Delete VPC
        ec2client.delete_vpc(VpcId=vpcid)
        LOGGER.info(
            "VPC %s and associated resources has been deleted.",
            vpcid,
        )
    except exceptions.ClientError:
        LOGGER.warning(
            "WARNING: cannot delete VPC %s in account %s",
            vpcid,
            account_id,
            exc_info=True,
        )
        raise


def delete_default_vpc(client, account_id, region, role):
    default_vpc_id = None
    max_retry_seconds = 360
    while True:
        try:
            vpc_response = client.describe_vpcs()
            break
        except exceptions.ClientError as client_error:
            if client_error.response["Error"]["Code"] == 'OptInRequired':
                LOGGER.warning(
                    'Passing on region %s as Opt-in is required.',
                    client.meta.region_name,
                )
                return
        except BaseException as error:
            LOGGER.warning(
                'Could not retrieve VPCs: %s}. '
                'Sleeping for 2 seconds before trying again.',
                error,
            )
            max_retry_seconds = + 2
            sleep(2)
            if max_retry_seconds <= 0:
                raise StopIteration(
                    "Could not describe VPCs within retry limit.",
                ) from error

    for vpc in vpc_response["Vpcs"]:
        if vpc["IsDefault"] is True:
            default_vpc_id = vpc["VpcId"]
            break

    if default_vpc_id is None:
        LOGGER.debug(
            "No default VPC found in account %s in the %s region",
            account_id,
            region,
        )
        return

    LOGGER.info(
        "Found default VPC Id %s in the %s region",
        default_vpc_id,
        region,
    )
    vpc_cleanup(account_id, default_vpc_id, role, region)
