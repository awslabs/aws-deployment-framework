"""
# vpc.py

Remove default VPC and related resources
"""
from time import sleep
import boto3
from botocore import exceptions
from logger import configure_logger
LOGGER = configure_logger(__name__)

def vpc_cleanup(vpcid, role, region):
    """Remove VPC from AWS
    Set your region/access-key/secret-key from env variables or boto config.
    :param vpcid: id of vpc to delete
    """
    if not vpcid:
        return
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

def delete_default_vpc(client, account_id, region, role):
    """Delete the default VPC in the given account id

        :param client: EC2 boto3 client instance
        :param account_id: AWS account id
        """
    # Check and remove default VPC
    default_vpc_id = None

    # Retrying the describe_vpcs call. Sometimes the VPC service is not ready when
    # you have just created a new account.
    max_retry_seconds = 360
    while True:
        try:
            vpc_response = client.describe_vpcs()
            break
        except exceptions.ClientError as e:
            if e.response["Error"]["Code"] == 'OptInRequired':
                LOGGER.warning(f'Passing on region {client.meta.region_name} as Opt-in is required.')
                return
        except BaseException as e:
            LOGGER.warning(f'Could not retrieve VPCs: {e}. Sleeping for 2 seconds before trying again.')
            max_retry_seconds = + 2
            sleep(2)
            if max_retry_seconds <= 0:
                raise Exception("Could not describe VPCs within retry limit.")


    for vpc in vpc_response["Vpcs"]:
        if vpc["IsDefault"] is True:
            default_vpc_id = vpc["VpcId"]
            break

    if default_vpc_id is None:
        LOGGER.debug(f"No default VPC found in account {account_id} in the {region} region")
        return

    LOGGER.info(f"Found default VPC Id {default_vpc_id} in the {region} region")
    vpc_cleanup(default_vpc_id, role, region)
    # subnet_response = client.describe_subnets()
    # default_subnets = [
    #     subnet
    #     for subnet in subnet_response["Subnets"]
    #     if subnet["VpcId"] == default_vpc_id
    # ]

    # LOGGER.info(f"Deleting default {len(default_subnets )} subnets")
    # for subnet in default_subnets:
    #     client.delete_subnet(SubnetId=subnet["SubnetId"], DryRun=dry_run)

    # igw_response = client.describe_internet_gateways()
    # try:
    #     default_igw = [
    #         igw["InternetGatewayId"]
    #         for igw in igw_response["InternetGateways"]
    #         for attachment in igw["Attachments"]
    #         if attachment["VpcId"] == default_vpc_id
    #     ][0]
    # except IndexError:
    #     default_igw = None

    # if default_igw:
    #     LOGGER.info(f"Detaching Internet Gateway {default_igw}")
    #     client.detach_internet_gateway(
    #         InternetGatewayId=default_igw, VpcId=default_vpc_id, DryRun=dry_run
    #     )

    #     LOGGER.info(f"Deleting Internet Gateway {default_igw}")
    #     client.delete_internet_gateway(
    #         InternetGatewayId=default_igw
    #     )

    # sleep(10)  # It takes a bit of time for the dependencies to clear
    # LOGGER.debug(f"Deleting Default VPC {default_vpc_id} for the {region} region")
    
    # delete_vpc_response = client.delete_vpc(VpcId=default_vpc_id, DryRun=dry_run)

    # return delete_vpc_response
