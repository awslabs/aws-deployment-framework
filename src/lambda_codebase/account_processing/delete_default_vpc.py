# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Deletes the default VPC in a particular region
"""
import os
from sts import STS
from aws_xray_sdk.core import patch_all
from logger import configure_logger

patch_all()

LOGGER = configure_logger(__name__)
ADF_ROLE_NAME = os.getenv("ADF_ROLE_NAME")


def assume_role(account_id):
    sts = STS()
    return sts.assume_cross_account_role(
        f"arn:aws:iam::{account_id}:role/{ADF_ROLE_NAME}",
        "adf_delete_default_vpc",
    )


def find_default_vpc(ec2_client):
    vpc_response = ec2_client.describe_vpcs()
    for vpc in vpc_response["Vpcs"]:
        if vpc["IsDefault"] is True:
            return vpc["VpcId"]
    return None


def delete_default_vpc(ec2_resource, ec2_client, default_vpc_id):
    vpc = ec2_resource.Vpc(default_vpc_id)

    LOGGER.info(f"Deleting gateways of VPC {default_vpc_id}")
    for gateway in vpc.internet_gateways.all():
        vpc.detach_internet_gateway(InternetGatewayId=gateway.id)
        gateway.delete()

    LOGGER.info(f"Deleting route tables associations of VPC {default_vpc_id}")
    for route_table in vpc.route_tables.all():
        for association in route_table.associations:
            if not association.main:
                association.delete()

    LOGGER.info(f"Deleting security groups of VPC {default_vpc_id}")
    for security_group in vpc.security_groups.all():
        if security_group.group_name != "default":
            security_group.delete()

    LOGGER.info(f"Deleting subnets and interfaces of VPC {default_vpc_id}")
    for subnet in vpc.subnets.all():
        for interface in subnet.network_interfaces.all():
            interface.delete()
        subnet.delete()

    LOGGER.info(f"Deleting default VPC {default_vpc_id}")
    ec2_client.delete_vpc(VpcId=default_vpc_id)



def lambda_handler(event, _):
    event = event.get("Payload")
    LOGGER.info(f"Checking for default VPC: {event.get('account_full_name')}")

    role = assume_role(account_id=event.get("account_id"))
    ec2_client = role.client("ec2", region_name=event.get("region"))

    default_vpc_id = find_default_vpc(ec2_client)
    if default_vpc_id:
        LOGGER.info(f"Default VPC found: {default_vpc_id} in {event.get('account_full_name')}")
        ec2_resource = role.resource("ec2", region_name=event.get("region"))
        delete_default_vpc(ec2_resource, ec2_client, default_vpc_id)

    return {"Payload": event}
