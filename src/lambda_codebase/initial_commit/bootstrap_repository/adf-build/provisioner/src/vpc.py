# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
        # detach and delete all gateways associated with the vpc
        for gw in vpc.internet_gateways.all():
            vpc.detach_internet_gateway(InternetGatewayId=gw.id)
            gw.delete()
        # Route table associations
        for rt in vpc.route_tables.all():
            for rta in rt.associations:
                if not rta.main:
                    rta.delete()
        # Security Group
        for sg in vpc.security_groups.all():
            if sg.group_name != 'default':
                sg.delete()
        # Network interfaces
        for subnet in vpc.subnets.all():
            for interface in subnet.network_interfaces.all():
                interface.delete()
            subnet.delete()
        # Delete vpc
        ec2client.delete_vpc(VpcId=vpcid)
        LOGGER.info(f"VPC {vpcid} and associated resources has been deleted.")
    except exceptions.ClientError:
        LOGGER.warning(
            f"WARNING: cannot delete VPC {vpcid} in account {account_id}",
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
        except exceptions.ClientError as e:
            if e.response["Error"]["Code"] == 'OptInRequired':
                LOGGER.warning(
                    f'Passing on region {client.meta.region_name} as Opt-in is required.')
                return
        except BaseException as e:
            LOGGER.warning(
                f'Could not retrieve VPCs: {e}. Sleeping for 2 seconds before trying again.')
            max_retry_seconds = + 2
            sleep(2)
            if max_retry_seconds <= 0:
                raise Exception(
                    "Could not describe VPCs within retry limit.",
                ) from e

    for vpc in vpc_response["Vpcs"]:
        if vpc["IsDefault"] is True:
            default_vpc_id = vpc["VpcId"]
            break

    if default_vpc_id is None:
        LOGGER.debug(
            f"No default VPC found in account {account_id} in the {region} region")
        return

    LOGGER.info(
        f"Found default VPC Id {default_vpc_id} in the {region} region")
    vpc_cleanup(account_id, default_vpc_id, role, region)
