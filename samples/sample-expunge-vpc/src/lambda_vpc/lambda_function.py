# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

from os import environ
import logging
import hashlib

from crhelper import CfnResource
import boto3

logger = logging.getLogger(__name__)

helper = CfnResource(
    json_logging=False,
    log_level='INFO',
    boto_level='CRITICAL'
)

REGION_NAME = environ['region_name']


def generate_dummy_resource_id(event):
    s = f"{event['StackId']}-{event['LogicalResourceId']}".encode('utf-8')
    hash_object = hashlib.sha256(s)
    physical_resource_id = hash_object.hexdigest()
    return physical_resource_id


def create_ec2_client(region_name, **kwargs):
    if 'profile' in kwargs:
        logger.info(
            "Creating Boto3 EC2 Client using profile: %s",
            kwargs['profile'],
        )
        session = boto3.Session(profile_name=kwargs['profile'])
        client = session.client('ec2', region_name=region_name)
    else:
        logger.info("Creating Boto3 EC2 Client using default config")
        client = boto3.client('ec2', region_name=region_name)
    return client


def delete_subnets(client, vpc_id):
    logger.info("Getting subnets for VPC")
    subnet_paginator = client.get_paginator('describe_subnets')
    subnet_pages = subnet_paginator.paginate(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id,
                ],
            },
        ],
    )
    for subnet in subnet_pages:
        logger.info("%d Subnets found", len(subnet['Subnets']))
        for s in subnet['Subnets']:
            logger.info("Deleting subnet with ID: %s", s['SubnetId'])
            client.delete_subnet(
                SubnetId=s['SubnetId'],
            )


def delete_internet_gateway(client, vpc_id):
    logger.info("Getting Internet Gateways attached to %s", vpc_id)
    igw_paginator = client.get_paginator('describe_internet_gateways')
    igw_pages = igw_paginator.paginate(
        Filters=[
            {
                'Name': 'attachment.vpc-id',
                'Values': [
                    vpc_id,
                ],
            },
        ],
    )
    for page in igw_pages:
        logger.info("%d Gateways found", len(page['InternetGateways']))
        for gw in page['InternetGateways']:
            logger.info(
                "Detaching internet gateway: %s from VPC",
                gw['InternetGatewayId'],
            )
            client.detach_internet_gateway(
                InternetGatewayId=gw['InternetGatewayId'],
                VpcId=vpc_id,
            )
            logger.info(
                "Deleting internet gateway: %s",
                gw['InternetGatewayId'],
            )
            client.delete_internet_gateway(
                InternetGatewayId=gw['InternetGatewayId'],
            )


def delete_route_tables(client, vpc_id):
    logger.info("Getting Route Tables attached to %s", vpc_id)
    route_table_paginator = client.get_paginator('describe_route_tables')
    route_table_pages = route_table_paginator.paginate(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id,
                ],
            },
        ],
    )
    for route_tables in route_table_pages:
        logger.info("%d Route Tables found", len(route_tables['RouteTables']))
        for route_table in route_tables['RouteTables']:
            for route in route_table['Routes']:
                if route['GatewayId'] != 'local':
                    client.delete_route(
                        DestinationCidrBlock=route['DestinationCidrBlock'],
                        RouteTableId=route_table['RouteTableId'],
                    )


def delete_security_groups(client, vpc_id):
    logger.info("Getting Security Groups attached to %s", vpc_id)
    security_group_paginator = client.get_paginator('describe_security_groups')
    security_group_pages = security_group_paginator.paginate(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id,
                ],
            },
        ],
    )
    for groups in security_group_pages:
        logger.info("%d Security Groups found", len(groups['SecurityGroups']))
        for group in groups['SecurityGroups']:
            if group['GroupName'] != "default":
                logger.info(
                    "Deleting non-default group: %s",
                    group['GroupName'],
                )
                client.delete_security_group(
                    GroupId=group['GroupId'],
                    GroupName=group['GroupName'],
                )


def remove_default_vpc(client):
    vpc_paginator = client.get_paginator('describe_vpcs')
    vpc_pages = vpc_paginator.paginate()
    for vpcs in vpc_pages:
        for vpc in vpcs['Vpcs']:
            if vpc['IsDefault']:
                logger.info("Default VPC found. VPC ID: %s", vpc['VpcId'])

                delete_subnets(client, vpc['VpcId'])

                delete_internet_gateway(client, vpc['VpcId'])

                delete_route_tables(client, vpc['VpcId'])

                delete_security_groups(client, vpc['VpcId'])

                logger.info("Deleting VPC: %s", vpc['VpcId'])
                client.delete_vpc(
                    VpcId=vpc['VpcId'],
                )


def get_regions(client):
    regions = client.describe_regions()
    return regions


@helper.create
def create(event, context):
    logger.info("Stack creation therefore default VPCs are to be removed")

    client = create_ec2_client(REGION_NAME)
    regions = get_regions(client)
    for region in regions['Regions']:
        logger.info("Creating ec2 client in %s region", region['RegionName'])
        logger.info(
            "Calling 'remove_default_vpc' function to remove default VPC and "
            "associated resources within the region",
        )
        ec2_client = create_ec2_client(region_name=region['RegionName'])
        remove_default_vpc(ec2_client)
        logger.info('~' * 72)

    # Items stored in helper.Data will be saved
    # as outputs in your resource in CloudFormation
    helper.Data.update({})
    # This is the Physical resource of your ID:
    return generate_dummy_resource_id(event)


@helper.update
def update(event, context):
    logger.info("Stack update therefore no real changes required on resources")
    # This is the Physical resource of your ID:
    return generate_dummy_resource_id(event)


@helper.delete
def delete(event, context):
    logger.info("Stack deletion therefore default VPCs are to be recreated")

    client = create_ec2_client(REGION_NAME)
    regions = get_regions(client)
    for region in regions['Regions']:
        logger.info("Creating ec2 client in %s region", region['RegionName'])
        ec2_client = create_ec2_client(region_name=region['RegionName'])
        vpc_paginator = ec2_client.get_paginator('describe_vpcs')
        vpc_pages = vpc_paginator.paginate()
        default_vpc_found = False
        for vpcs in vpc_pages:
            for vpc in vpcs['Vpcs']:
                if vpc['IsDefault']:
                    default_vpc_found = True
        if not default_vpc_found:
            logger.info("Creating default VPC in region")
            ec2_client.create_default_vpc()

        logger.info('~' * 72)

    # This is the Physical resource of your ID
    return generate_dummy_resource_id(event)


def lambda_handler(event, context):
    helper(event, context)
