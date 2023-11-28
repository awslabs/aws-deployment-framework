# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
S3 module used throughout the ADF
"""

import boto3

from logger import configure_logger
from partition import (
    get_aws_domain,
    get_partition
)


LOGGER = configure_logger(__name__)


class S3:
    """
    Class used for modeling S3
    """

    def __init__(self, region, bucket):
        self.region = region
        self.client = boto3.client('s3', region_name=region)
        self.resource = boto3.resource('s3', region_name=region)
        self.bucket = bucket
        self.domain_suffix = get_aws_domain(region)
        self.partition = get_partition(region)

    @staticmethod
    def supported_path_styles():
        """
        Fetch the list of supported path styles.

        Returns:
            list(str): The list of supported path styles.
        """
        return [
            'path',
            's3-key-only',
            's3-uri',
            's3-url',
            'virtual-hosted',
        ]

    def build_pathing_style(self, style, key):
        """
        Return the requested path for the S3 bucket and key.

        Args:
            style (str): The path style. Valid options are:
                's3-url' returns: 's3://{bucket}/{key}'
                's3-uri' returns: '{bucket}/{key}'
                's3-key-only' return: '{key}'
                'path': returns: 'https://{s3-region}.{self.domain_suffix}/{bucket}/{key}'
                'virtual-hosted' returns: 'https://{buycket}.{s3-region}.{self.domain_suffix}/{key}'

            key (str): The object key to include in the path.

        Returns:
            str: The path to the bucket and/or key in the style requested.
        """
        if style == 's3-url':
            return f"s3://{self.bucket}/{key}"
        if style == 's3-uri':
            return f"{self.bucket}/{key}"
        if style == 's3-key-only':
            return key

        s3_region_name = "s3"
        if self.region != 'us-east-1':
            s3_region_name = f"s3-{self.region}"

        if style == 'path':
            if self.partition == "aws-cn":
                return f"https://{self.bucket}.s3.{self.region}.{self.domain_suffix}/{key}"
            return f"https://{s3_region_name}.{self.domain_suffix}/{self.bucket}/{key}"
        if style == 'virtual-hosted':
            return f"https://{self.bucket}.{s3_region_name}.{self.domain_suffix}/{key}"


        raise Exception(
            f"Unknown upload style syntax: {style}. "
            "Valid options include: s3-uri, path, or "
            "virtual-hosted."
        )

    def put_object(self, key, file_path, style="path", pre_check=False, object_acl='private'):
        """
        Put the object into S3 and return the reference to the object
        in the requested path style.

        Args:
            key (str): The S3 object key to check and/or write to.

            file_path (str): The file to upload using binary write mode.

            style (str): The path style to use when returning the S3 object
                location. Valid values are listed in this class using the
                static method: supported_path_styles.

            pre_check (bool): Whether or not to check if the file exists
                in the S3 bucket already. When set to True, it will only
                upload if the object does not exist yet. When set to False
                it will always perform the upload, whether the object already
                exists or not. Be aware, the contents of the object and the
                given file are not compared. Only whether the given object key
                exists in the bucket or not.

            object_acl (str): Set the object ACL when uploading the object.
                Directly passed to boto3. Valid values are:
                ACL='private'|'public-read'|'public-read-write'|
                'authenticated-read'|'aws-exec-read'|'bucket-owner-read'|
                'bucket-owner-full-control'

        Returns:
            str: The S3 object reference in the requested path style. This
                will be returned regardless of whether or not an upload was
                performed or not. In case the object key existed before, and
                pre_check was set to True, calling this function will only
                return the reference path to the object.
        """
        # Do we need to upload the file to the bucket?
        # If we don't need to check first, do. Otherwise, check if it exists
        # first and only upload if it does not exist.
        if not pre_check or not self._does_object_exist(key):
            self._perform_put_object(key, file_path, object_acl)
        return self.build_pathing_style(style, key)

    def _does_object_exist(self, key):
        """
        Check whether the given S3 object key exists in this bucket or not.

        Args:
            key (str): The S3 object key to check.

        Returns:
            bool: True when the object exists, False when it does not.
        """
        try:
            self.client.get_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.NoSuchKey:
            return False

    def _perform_put_object(self, key, file_path, object_acl="private"):
        """
        Perform actual put operation without any checks.
        This is called internally by the put_object method when the
        requested file needs to be uploaded.

        Args:
            key (str): They S3 key of the object to put the file contents to.

            file_path (str): The file to upload using binary write mode.

            object_acl (str): The object ACL to be applied.
        """
        try:
            LOGGER.info(
                "Uploading %s as %s to S3 Bucket %s in %s",
                file_path,
                key,
                self.bucket,
                self.region,
            )
            with open(file_path, mode='rb') as file_handler:
                self.resource.Object(self.bucket, key).put(
                    ACL=object_acl,
                    Body=file_handler,
                )
                LOGGER.debug("Upload of %s was successful.", key)
        except BaseException:
            LOGGER.error("Failed to upload %s", key, exc_info=True)
            raise

    def read_object(self, key):
        """
        Read the object from S3.

        Args:
            key (str): The object key.

        Returns:
            str: The content of the object decoded using utf-8.
        """
        s3_object = self.resource.Object(self.bucket, key)
        return s3_object.get()['Body'].read().decode('utf-8')

    def fetch_s3_url(self, key):
        """
        Recursively search for an object in S3 and return its URL
        """
        try:
            s3_object = self.resource.Object(self.bucket, key)
            s3_object.get()
            LOGGER.debug('Found Template at: %s', s3_object.key)
            if self.region == 'us-east-1':
                return f"https://s3.{self.domain_suffix}/{self.bucket}/{key}"
            if self.partition == 'aws-cn':
                return self.build_pathing_style("path", key)
            return f"https://s3-{self.region}.{self.domain_suffix}/{self.bucket}/{key}"
        except self.client.exceptions.NoSuchKey:
            # Split the path to remove the last key entry from the string
            key_level_up = key.split('/')
            # Return None here if nothing could be found from recursive
            # searching
            if len(key_level_up) == 1:
                LOGGER.debug(
                    'Nothing could be found for %s when traversing the bucket', key)
                return []

            LOGGER.debug(
                'Unable to find the specified Key: %s - looking one level up', key)
            # remove the key name in which we did not find the file we wanted this attempt
            # (-1 will be json/yml file, -2 will be the key prefix) which we want to leave
            del key_level_up[-2]

            # Join it back together, and recursive call the function with the
            # new trimmed key until a template/params is found
            next_level_up_key = '/'.join(key_level_up)
            return self.fetch_s3_url(next_level_up_key)
