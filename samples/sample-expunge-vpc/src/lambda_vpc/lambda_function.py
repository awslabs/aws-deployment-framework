from crhelper import CfnResource
import logging
import boto3
from os import environ
import hashlib

logger = logging.getLogger(__name__)

helper = CfnResource(
    json_logging=False,
    log_level='INFO',
    boto_level='CRITICAL'
)

region_name = environ['region_name']


def generate_dummy_resource_id(event):
    s = f"{event['StackId']}-{event['LogicalResourceId']}".encode('utf-8')
    hash_object = hashlib.sha256(s)
    physical_resource_id = hash_object.hexdigest()
    return physical_resource_id


def create_ec2_client(region_name, **kwargs):
    if 'profile' in kwargs:
        logger.info("Creating Boto3 EC2 Client using profile: {}".format(kwargs['profile']))
        session = boto3.Session(profile_name=kwargs['profile'])
        client = session.client('ec2', region_name=region_name)
    else:
        logger.info("Creating Boto3 EC2 Client using default config")
        client = boto3.client('ec2', region_name=region_name)
    return client


def delete_subnets(client, vpc_id):
    logger.info("Getting subnets for VPC")
    subnet = client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id
                ]
            }
        ]
    )
    logger.info(f"{len(subnet['Subnets'])} Subnets found")
    for s in subnet['Subnets']:
        logger.info(f"Deleting subnet with ID: {s['SubnetId']}")
        client.delete_subnet(
            SubnetId=s['SubnetId']
        )


def delete_internet_gateway(client, vpc_id):
    logger.info(f"Getting Internet Gateways attached to {vpc_id}")
    igw = client.describe_internet_gateways(
        Filters=[
            {
                'Name': 'attachment.vpc-id',
                'Values': [
                    vpc_id,
                ]
            },
        ]
    )
    logger.info(f"{len(igw['InternetGateways'])} Gateways found")
    for gw in igw['InternetGateways']:
        logger.info(f"Detaching internet gateway: {gw['InternetGatewayId']} from VPC")
        client.detach_internet_gateway(
            InternetGatewayId=gw['InternetGatewayId'],
            VpcId=vpc_id
        )
        logger.info(f"Deleting internet gateway: {gw['InternetGatewayId']}")
        client.delete_internet_gateway(
            InternetGatewayId=gw['InternetGatewayId']
        )


def delete_route_tables(client, vpc_id):
    logger.info(f"Getting Route Tables attached to {vpc_id}")
    route_tables = client.describe_route_tables(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id
                ]
            },
        ]
    )
    logger.info(f"{len(route_tables['RouteTables'])} Route Tables found")
    for route_table in route_tables['RouteTables']:
        for route in route_table['Routes']:
            if route['GatewayId'] != 'local':
                client.delete_route(
                    DestinationCidrBlock=route['DestinationCidrBlock'],
                    RouteTableId=route_table['RouteTableId']
                )


def delete_security_groups(client, vpc_id):
    logger.info(f"Getting Security Groups attached to {vpc_id}")
    groups = client.describe_security_groups(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id
                ]
            },
        ])
    logger.info(f"{len(groups['SecurityGroups'])} Security Groups found")
    for group in groups['SecurityGroups']:
        if group['GroupName'] != "default":
            logger.info(f"Deleting non default group: {group['GroupName']}")
            client.delete_security_group(
                GroupId=group['GroupId'],
                GroupName=group['GroupName']
            )


def remove_default_vpc(client):
    vpcs = client.describe_vpcs()
    for vpc in vpcs['Vpcs']:
        if vpc['IsDefault']:
            logger.info(f"Default VPC found. VPC ID: {vpc['VpcId']}")

            delete_subnets(client, vpc['VpcId'])

            delete_internet_gateway(client, vpc['VpcId'])

            delete_route_tables(client, vpc['VpcId'])

            delete_security_groups(client, vpc['VpcId'])

            logger.info(f"Deleting VPC: {vpc['VpcId']}")
            client.delete_vpc(
                VpcId=vpc['VpcId']
            )


def get_regions(client):
    regions = client.describe_regions()
    return regions


@helper.create
def create(event, context):
    logger.info("Stack creation therefore default VPCs are to be removed")

    client = create_ec2_client(region_name)
    regions = get_regions(client)
    for region in regions['Regions']:
        logger.info(f"Creating ec2 client in {region['RegionName']} region")
        logger.info(
            "Calling 'remove_default_vpc' function to remove default VPC and associated resources within the region")
        ec2_client = create_ec2_client(region_name=region['RegionName'])
        remove_default_vpc(ec2_client)
        logger.info('~' * 72)

    # Items stored in helper.Data will be saved
    # as outputs in your resource in CloudFormation
    helper.Data.update({})
    return generate_dummy_resource_id(event)  # This is the Physical resource of your ID


@helper.update
def update(event, context):
    logger.info("Stack update therefore no real changes required on resources")
    return generate_dummy_resource_id(event)  # This is the Physical resource of your ID


@helper.delete
def delete(event, context):
    logger.info("Stack deletion therefore default VPCs are to be recreated")

    client = create_ec2_client(region_name)
    regions = get_regions(client)
    for region in regions['Regions']:
        logger.info(f"Creating ec2 client in {region['RegionName']} region")
        ec2_client = create_ec2_client(region_name=region['RegionName'])
        vpcs = ec2_client.describe_vpcs()
        if len(vpcs['Vpcs']) == 0:
            logger.info("Creating default VPC in region")
            ec2_client.create_default_vpc()
        else:
            for vpc in vpcs['Vpcs']:
                if not vpc['IsDefault']:
                    logger.info("Creating default VPC in region")
                    ec2_client.create_default_vpc()

        logger.info('~' * 72)

    return generate_dummy_resource_id(event)  # This is the Physical resource of your ID


def lambda_handler(event, context):
    helper(event, context)
