# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Deletes the default VPC in a particular region
"""
import os
from sts import STS
from aws_xray_sdk.core import patch_all
patch_all()

ADF_ROLE_NAME = os.getenv("ADF_ROLE_NAME")


def lambda_handler(event, _):
    event = event.get("Payload")
    print(f"Deleting Default vpc: {event.get('account_full_name')}")
    sts = STS()
    account_id = event.get("account")

    role = sts.assume_cross_account_role(
        f"arn:aws:iam::{account_id}:role/{ADF_ROLE_NAME}",
        "adf_delete_default_vpc",
    )
    ec2_client = role.client("ec2", region_name=event.get("region"))
    vpc_response = ec2_client.describe_vpcs()
    default_vpc_id = None
    for vpc in vpc_response["Vpcs"]:
        if vpc["IsDefault"] is True:
            default_vpc_id = vpc["VpcId"]
    if default_vpc_id:
        ec2 = role.resource("ec2", region_name=event.get("region"))
        vpc = ec2.Vpc(default_vpc_id)
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
            if sg.group_name != "default":
                sg.delete()
        for subnet in vpc.subnets.all():
            for interface in subnet.network_interfaces.all():
                interface.delete()
            subnet.delete()
        ec2_client.delete_vpc(VpcId=default_vpc_id)
    return {"Payload": event}
