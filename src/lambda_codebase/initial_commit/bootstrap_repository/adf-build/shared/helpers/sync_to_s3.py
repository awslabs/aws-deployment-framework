# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""
Sync files to an S3 Bucket.

This script will only overwrite files when the content changed.
To determine a file changed, it will calculate the SHA-256 hash of the file
and match that against the object SHA256 hash metadata stored along with the
S3 object.

If a file is stored inside the S3 Bucket that is no longer present
locally, it will clean it up too.

Usage:
    sync_to_s3.py [-v... | --verbose...] [-r | --recursive] [-d | --delete]
            [-e <extension> | --extension <extension>]...
            [--metadata <key>=<value>]...
            [--upload-with-metadata <key>=<value>]...
            [--]
            SOURCE_PATH DESTINATION_S3_URL

    sync_to_s3.py -h | --help

    sync_to_s3.py --version

Options:
    -d, --delete
                Delete stale files that are located in the destination bucket
                with the corresponding S3 prefix. For example, if the
                destination is set to s3://my-bucket/my-prefix, it will sync
                all files inside the prefix location. If a file is located
                there, that is not present in the source path locally, it will
                get deleted. But only if the file extension of that path
                matches (if one is specified).

    -e, --extension <extension>
                File extension filter. Files that match locally are only
                uploaded if their extension matches. If this parameter is not
                specified, it will not apply a filter. Matching all files that
                are found locally. The same filter is also applied on the
                destination. For example, if the destination S3 location
                contains a README.md file, while the extension is configured
                to match '.yml', it will not delete the README.md file as its
                extension is not a match.

    -h, --help  Show this help message.

    --metadata <key>=<value>
                The key and value pairs that are passed with this argument
                will be added to the metadata. If the metadata set using this
                argument does not match the metadata on the S3 object, it will
                perform an update too.

    -r, --recursive
                Indicating that the <source_path> is a directory, and it
                should recursively walk through the source directories and sync
                those to the S3 bucket.

    --upload-with-metadata <key>=<value>
                When a file is uploaded, the key and value pairs that are
                passed with this argument will be added. It will only apply
                these metadata properties if the file is missing, or the
                content of the file or any of the `--metadata` properties did
                not match.

    -v, --verbose
                Show verbose logging information.

    <source_path>
                The source path where the original files are stored that should
                by synced to the destination bucket. When you specify a
                directory as the source path it will copy the files inside the
                directory to the S3 bucket if you also specify the recursive
                flag. Otherwise it will treat the source path as a file, when a
                directory is detected instead it will abort with an error.
                If the source path is a directory, the object keys that are
                derived from the files inside the directory will be relative to
                the <source_path>. For example, if the <source_path> equals
                `./adf-accounts`, which contains a file named
                `adf-accounts/adf.yml`, it will copy the file as `adf.yml`.
                If the prefix of the s3 bucket is set to `adf-s3-accounts`, the
                final key of that specific file will be:
                `adf-s3-accounts/adf.yml`.
                If the <source_path> is a file and
                the recursive flag is not specified, it will expect that the
                s3 prefix is the new object name instead. In this case, if
                <source_path> equals `./deployment_map.yml` and the s3 prefix
                is `root_deployment_map.yml`, it will copy the file to the s3
                prefix key.

    <destination_s3_url>
                The destination bucket and its prefix where the files should be
                copied to. The s3 bucket and its optional prefix should be
                specified as: s3://your-bucket-name/your-optional-prefix.
                In this case, `your-bucket-name` is the name of the bucket.
                While `your-optional-prefix` is the name of the prefix used for
                all files that are copied to S3. If a directory is copied, i.e.
                recursive is set, it will prepend the prefix to the object
                keys of the files that are synced. If a file is copied instead,
                i.e. no --recurdive, it will use the s3 prefix as the target
                object key to use for that file.

Examples:

    Copy the deployment_map.yml file to an S3 bucket as
    root_deployment_map.yml, and delete the root_deployment_map.yml if the
    local deployment_map.yml file is missing:

        $ python sync_to_s3.py -d deployment_map.yml \\
            s3://deploy-bucket/root_deployment_map.yml

    Copy all .yml files from the deployment_maps folder to an S3 bucket where
    the objects are prefixed with the `deployment_map/`, deleting the .yml
    objects inside the deployment_map that no longer exist locally.

        $ python sync_to_s3.py -d -e .yml -r deployment_maps \\
            s3://deploy-bucket/deployment_maps

    Copy all .yml files from folder source_folder to the to an S3 bucket where
    the objects are prefixed with the `object_folder/`, deleting the .yml
    objects inside the YAML files that no longer exist locally. Additionally,
    all files will get the metadata set to include `adf_version`. And if the
    file is uploaded/updated, it will also apply the `execution_id` metadata.

        $ python sync_to_s3.py -d -e .yml -r source_folder \\
            --metadata "adf_version=x.y.z" \\
            --upload-with-metadata "execution_id=$EXEC_ID" \\
            s3://deploy-bucket/object_folder
"""

import os
import sys
from typing import Mapping, TypedDict
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import logging
import base64
import boto3
from docopt import docopt


ADF_VERSION = os.environ.get("ADF_VERSION")
ADF_LOG_LEVEL = os.environ.get("ADF_LOG_LEVEL", "INFO")
NON_RECURSIVE_KEY = '%%-single-match-%%'

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(ADF_LOG_LEVEL)


class GenericFileData(TypedDict):
    """
    Generic File or Object Data class.
    """
    key: str


class LocalFileData(GenericFileData):
    """
    Local File Data class, extended from the GenericFileData.
    """
    file_path: str
    sha256_hash: str


class S3ObjectData(GenericFileData):
    """
    S3 Object Data class, extended from the GenericFileData.
    """
    metadata: dict[str, str]


class MetadataToCheck(TypedDict):
    always_apply: dict[str, str]
    upon_upload_apply: dict[str, str]


def get_local_files(
    local_path: str,
    file_extensions: [str],
    recursive: bool,
) -> Mapping[str, LocalFileData]:
    """
    Retrieve the files that are in the relative path local_path.
    This will perform a search inside a directory if the local_path is a
    directory and the recursive flag is set. Alternatively, it will determine
    if a specific file exists and if so, it will retrieve that one only.

    Args:
        local_path (str): The local path to search in/lookup.

        file_extensions ([str]): The file_extensions to search for, or empty
            list if this filter should not be applied.

        recursive (bool): Whether to search recursively or not.

    Returns:
        Mapping[str, LocalFileData]: The map of the Local File Data objects
            representing the local file(s) that were found.
            The keys of the map are derived from the local file path relative
            to the local_path. With a single object, the key used is
            a special non recursive identifier key instead.
            The value of the map is the Local File Data.
    """
    if recursive:
        return _get_recursive_local_files(
            local_path,
            file_extensions,
        )
    return _get_single_local_file(
        local_path,
    )


def _get_recursive_local_files(
    local_path: str,
    file_extensions: [str],
) -> Mapping[str, LocalFileData]:
    """
    Retrieve the files that are in the relative path local_path.
    A search is performed using the specified glob if one is specified.
    Do not specify the glob in case only a single file should be matched.

    Args:
        local_path (str): The local files to search in.

        file_extensions ([str]): The file_extensions to search for, or empty
            list if this filter should not be applied. This will be converted
            to a glob search, where the extension ".yml" will match files with
            the glob search "**/*.yml", returning any YAML file that ends with
            .yml. Including those in subdirectories.

    Returns:
        Mapping[str, LocalFileData]: The map of the Local File Data objects
            representing the local files that were found.
            The keys of the map are derived from the local file path relative
            to the local_path.
            The value of the map is the Local File Data.
    """
    path = get_full_local_path(local_path)
    LOGGER.debug(
        "Searching for local files in %s matching %s",
        str(path),
        file_extensions,
    )
    local_files = {}
    globs_to_match = [
        f"**/*{ext}"
        for ext in (
            # File extensions or a list of an empty string, so it either
            # generates "**/*{ext}" for each extension in file_extensions
            # or it generates "**/*"
            file_extensions or [""]
        )
    ]
    for glob in globs_to_match:
        for file_path in path.glob(glob):
            local_file_data = _get_local_file_data(file_path, path)
            local_files[local_file_data['key']] = local_file_data

    LOGGER.debug(
        "Found %d local files: %s",
        len(local_files.keys()),
        local_files,
    )
    return local_files


def _get_single_local_file(
    local_path: str,
) -> Mapping[str, LocalFileData]:
    """
    Retrieve the file that is at the relative path local_path, or None if that
    does not exist.

    Args:
        local_path (str): The local files to search in.

    Returns:
        Mapping[str, LocalFileData]: The map of the Local File Data object
            representing the local file if one is found.
            The keys of the map are derived from the local file path relative
            to the local_path.
            The value of the map is the Local File Data.
    """
    path = get_full_local_path(local_path)
    LOGGER.debug(
        "Checking if local file at %s exists",
        str(path),
    )
    local_files = {}
    if path.exists():
        local_file_data = _get_local_file_data(path, path.parent)
        local_files[NON_RECURSIVE_KEY] = local_file_data
        LOGGER.debug(
            "File exists: %s",
            local_files,
        )
    else:
        LOGGER.debug(
            "File does not exist at: %s",
            path,
        )

    return local_files


def _get_local_file_data(
    file_path: Path,
    relative_to_path: Path,
) -> LocalFileData:
    """
    Get the local file data for the given path.

    This will open the file, calculate its hash and return that
    with in a LocalFileData object.

    Args:
        file_path (Path): The path of the file to read.

        relative_to_path (Path): The path that should be used to determine the
            relative path of the local file. If an object lives inside
            `x_path/y_path`. And the relative_to_path is set to `x_path`, the
            key of the local file will become: `y_path`.

    Returns:
        LocalFileData: The LocalFileData instance that holds the file
            information such as the sha256_hash, its relative path, etc.
    """
    with open(file_path, "rb", buffering=0) as file_pointer:
        file_hash = hashlib.sha256()
        memory_view = memoryview(bytearray(1024*1024))
        while data_read := file_pointer.readinto(memory_view):
            file_hash.update(memory_view[:data_read])
        relative_path = str(file_path.relative_to(relative_to_path))
        return {
            "key": relative_path,
            "file_path": str(file_path),
            "sha256_hash": str(base64.b64encode(file_hash.digest())),
        }


def get_s3_objects(
    s3_client: any,
    s3_bucket: str,
    s3_prefix: str,
    file_extensions: [str],
    recursive: bool,
):
    """
    Retrieve the object or objects that are stored inside the S3 bucket.
    When asked to search recursively, it will perform a search on the S3 bucket
    using the specified prefix and file extension.
    While it will perform a single object lookup otherwise.

    Args:
        s3_client (Boto3.Client): The Boto3 S3 Client to interact with when
            a file needs to be deleted.
        s3_bucket (str): The bucket name.
        s3_prefix (str): The prefix under which the objects are stored in
            the bucket.
        file_extensions ([str]): The file extensions of objects that would
            match.
        recursive (bool): Whether to search recursively or not.

    Returns:
        Mapping[str, S3ObjectData]: The map of the S3 objects that were
            found.
    """
    if recursive:
        return _get_recursive_s3_objects(
            s3_client,
            s3_bucket,
            s3_prefix,
            file_extensions,
        )

    return _get_single_s3_object(
        s3_client,
        s3_bucket,
        s3_prefix,
    )


def _get_recursive_s3_objects(
    s3_client: any,
    s3_bucket: str,
    s3_prefix: str,
    file_extensions: [str],
) -> Mapping[str, S3ObjectData]:
    """
    Retrieve the objects that are stored inside the S3 bucket, which keys
    start with the specified s3_prefix.

    Args:
        s3_client (Boto3.Client): The Boto3 S3 Client to interact with when
            a file needs to be deleted.
        s3_bucket (str): The bucket name.
        s3_prefix (str): The prefix under which the objects are stored in
            the bucket.
        file_extensions ([str]): The file extension of objects that would
            match.

    Returns:
        Mapping[str, S3ObjectData]: The map of the S3 objects that were
            found. The keys of the map are derived from the object key relative
            to the s3_prefix. Unless the key is equal to the s3_prefix, in that
            case the full object key is used as the key. The value of the map
            is the S3 Object Data.
    """
    LOGGER.debug(
        "Searching for S3 objects in s3://%s/%s",
        s3_bucket,
        s3_prefix,
    )
    s3_list_objects_paginator = s3_client.get_paginator("list_objects_v2")
    s3_object_iterator = s3_list_objects_paginator.paginate(
        Bucket=s3_bucket,
        Prefix=f"{s3_prefix}/",
    )
    s3_objects = {}
    for response_data in s3_object_iterator:
        for obj in response_data.get("Contents", []):
            matched_extensions = list(
                # The filter matches its Key against the file_extensions
                # to see if it ends with that specific extension.
                # This will return an empty list if it did not match or
                # if the file_extensions is empty.
                filter(obj.get("Key").endswith, file_extensions)
            )
            if file_extensions and not matched_extensions:
                # If we should filter on extensions and we did not match
                # with any, we should skip this object.
                continue
            index_key = convert_to_local_key(obj.get("Key"), s3_prefix)
            s3_objects[index_key] = _get_s3_object_data(
                s3_client,
                s3_bucket,
                obj.get("Key"),
            )

    LOGGER.debug(
        "Found %d S3 objects at: s3://%s/%s: %s",
        len(s3_objects.keys()),
        s3_bucket,
        s3_prefix,
        s3_objects,
    )
    return s3_objects


def _get_single_s3_object(
    s3_client: any,
    s3_bucket: str,
    s3_object_key: str,
) -> Mapping[str, S3ObjectData]:
    """
    Retrieve a single object that is stored inside the S3 bucket, which object
    key equals the specified s3_object_key.

    Args:
        s3_client (Boto3.Client): The Boto3 S3 Client to interact with when
            a file needs to be deleted.
        s3_bucket (str): The bucket name.
        s3_object_key (str): The object key under which the object might or
            should be stored in the bucket.

    Returns:
        Mapping[str, S3ObjectData]: The map of the S3 objects that were
            found. The keys of the map is set to the non recursive identifier.
            The value of the map is the S3 Object Data.
    """
    LOGGER.debug(
        "Searching for S3 object in s3://%s/%s",
        s3_bucket,
        s3_object_key,
    )
    s3_object_data = _get_s3_object_data(
        s3_client,
        s3_bucket,
        s3_object_key,
    )
    if not s3_object_data:
        return {}

    s3_objects = {}
    s3_objects[NON_RECURSIVE_KEY] = s3_object_data

    LOGGER.debug(
        "Found S3 object at: s3://%s/%s: %s",
        s3_bucket,
        s3_object_key,
        s3_objects,
    )
    return s3_objects


def _get_s3_object_data(s3_client, s3_bucket, key):
    try:
        obj_data = s3_client.head_object(
            Bucket=s3_bucket,
            Key=key,
        )
        return {
            "key": key,
            "metadata": obj_data.get("Metadata", {}),
        }
    except s3_client.exceptions.NoSuchKey:
        LOGGER.debug(
            "Could not find s3://%s/%s",
            s3_bucket,
            key,
        )
        return None


def upload_changed_files(
    s3_client: any,
    s3_bucket: str,
    s3_prefix: str,
    local_files: Mapping[str, LocalFileData],
    s3_objects: Mapping[str, S3ObjectData],
    metadata_to_check: MetadataToCheck,
):
    """
    Upload changed files, by looping over the local files found and checking
    if these still exist in the S3 bucket as objects. If they do, the SHA256
    hash is compared. The file is uploaded to the bucket if the file is
    missing or when the SHA256 hash does not match.

    Args:
        s3_client (Boto3.Client): The Boto3 S3 Client to interact with when
            a file needs to be deleted.

        s3_bucket (str): The bucket name.

        s3_prefix (str): The prefix under which the objects are stored in
            the bucket.

        local_files (Mapping[str, LocalFileData]): The map of LocalFileData
            objects, representing the files that were found locally.

        s3_objects (Mapping[str, S3ObjectData]): The map of S3ObjectData
            objects representing the objects that were found in the S3 bucket.

        metadata_to_check (MetadataToCheck): The metadata that needs to be
            applied all the time and upon upload only.
    """
    for key, local_file in local_files.items():
        s3_file = s3_objects.get(key)

        object_is_missing = s3_file is None
        s3_metadata = {} if object_is_missing else s3_file["metadata"]
        content_changed = (
            s3_metadata.get("sha256_hash") != local_file.get("sha256_hash")
        )
        metadata_changed = (
            dict(filter(
                lambda item: item[0] in metadata_to_check["always_apply"],
                s3_metadata.items(),
            )) != metadata_to_check["always_apply"]
        )
        if (object_is_missing or content_changed or metadata_changed):
            with open(local_file.get("file_path"), "rb") as file_pointer:
                s3_key = convert_to_s3_key(key, s3_prefix)

                LOGGER.info(
                    "Uploading file %s to s3://%s/%s because the %s",
                    local_file.get("file_path"),
                    s3_bucket,
                    s3_key,
                    (
                        "object does not exist yet" if object_is_missing
                        else (
                            "file content changed" if content_changed
                            else "metadata changed"
                        )
                    ),
                )
                s3_client.put_object(
                    Body=file_pointer,
                    Bucket=s3_bucket,
                    Key=s3_key,
                    Metadata={
                        **metadata_to_check['always_apply'],
                        **metadata_to_check['upon_upload_apply'],
                        "sha256_hash": local_file.get("sha256_hash"),
                    }
                )


def delete_stale_objects(
    s3_client: any,
    s3_bucket: str,
    s3_prefix: str,
    local_files: Mapping[str, LocalFileData],
    s3_objects: Mapping[str, S3ObjectData],
):
    """
    Delete stale files, by looping over the objects found in S3 and checking
    if these still exist locally. If not, they are stale and need to be
    deleted.

    Args:
        s3_client (Boto3.Client): The Boto3 S3 Client to interact with when
            a file needs to be deleted.
        s3_bucket (str): The bucket name.
        s3_prefix (str): The prefix under which the objects are stored in
            the bucket.
        local_files (Mapping[str, LocalFileData]): The map of LocalFileData
            objects, representing the files that were found locally.
        s3_objects (Mapping[str, S3ObjectData]): The map of S3ObjectData
            objects representing the objects that were found in the S3 bucket.
    """
    to_delete = []
    for key in s3_objects.keys():
        if local_files.get(key) is None:
            s3_key = convert_to_s3_key(key, s3_prefix)
            to_delete.append({
                "Key": s3_key,
            })

    if to_delete:
        LOGGER.info(
            "Deleting stale objects in s3://%s: %s",
            s3_bucket,
            to_delete,
        )
        s3_client.delete_objects(
            Bucket=s3_bucket,
            Delete={
                "Objects": to_delete,
            },
        )


def clean_s3_prefix(original_prefix: str) -> str:
    """
    Clean the S3 prefix, such that it does not start with a slash
    and does not end with a slash.

    i.e. `/some/path/` will become `some/path`

    Args:
        original_prefix (str): The original prefix that should be cleaned.

    Returns:
        str: The cleaned prefix.
    """
    new_prefix = (
        original_prefix[1:] if original_prefix.startswith("/")
        else original_prefix
    )

    if original_prefix.endswith("/"):
        return new_prefix[:-1]

    return new_prefix


def get_full_local_path(local_path: str) -> Path:
    """
    Convert the local path str to the full Path.

    Args:
        local_path (Path): The path where it should run the search from.
            Can be an absolute path or a relative path to the current working
            directory. Both will be translated to a full Path.

    Returns:
        Path: The full Path instance pointing to the local_path
            relative to the directory this command was executed from. Or the
            Path instance pointing to the local_path if that is an absolute
            path already.
    """
    path = Path(local_path)
    if path.is_absolute():
        return path

    here = Path(os.getcwd())
    return here / path


def convert_to_s3_key(local_key, s3_prefix):
    """
    Convert the local key to an S3 key.

    Args:
        local_key (str): The local key of the file (relative to the directory).
        s3_prefix (str): The S3 prefix that is in use.

    Returns:
        str: Returns the s3_prefix if that matches the local_key.
            When it did not match, it returns the `/{s3_prefix}/{local_key}`
    """
    if s3_prefix and local_key == NON_RECURSIVE_KEY:
        return s3_prefix

    if s3_prefix and local_key != s3_prefix:
        return f"{s3_prefix}/{local_key}"

    return local_key


def convert_to_local_key(s3_key, s3_prefix):
    """
    Convert the S3 key to a local key.

    Args:
        s3_key (str): The s3 key of the object includes the s3 prefix.
        s3_prefix (str): The S3 prefix that is in use.

    Returns:
        str: Returns the local key if that matches the s3_prefix.
            When it did not match, it removes the s3 prefix and returns
            the relative local_key.
    """
    if s3_prefix and s3_key != s3_prefix:
        return str(Path(s3_key).relative_to(s3_prefix))

    return s3_key


def ensure_valid_input(
    local_path: str,
    file_extensions: [str],
    s3_url: str,
    s3_bucket: str,
    s3_prefix: str,
    recursive: bool,
):
    if not local_path:
        LOGGER.error(
            "Input error: You need to specify the source path!"
        )
        sys.exit(1)

    if not s3_url:
        LOGGER.error(
            "Input error: You need to specify the destination S3 url!"
        )
        sys.exit(2)

    if not recursive and not s3_prefix:
        LOGGER.error(
            "Input error: Requested to sync single object, but no S3 object "
            "location was specified! "
        )
        LOGGER.error(
            "In case you would like to sync a single object "
            "to %s, you will need to specify the full object location. "
            "For example, s3://%s/this-is-the-target-object-location.yml",
            s3_url,
            s3_bucket,
        )
        sys.exit(3)

    full_path = get_full_local_path(local_path)
    if recursive and not full_path.exists():
        LOGGER.error(
            "Input error: The source path %s does not exist!",
            local_path,
        )
        sys.exit(4)

    if not recursive and full_path.exists() and full_path.is_dir():
        LOGGER.error(
            "Input error: When syncing a single file the source path %s "
            "should be referencing a file not a directory!",
            local_path,
        )
        sys.exit(5)

    if file_extensions and not recursive:
        LOGGER.warning("Input warning: Ignoring file_extension filter.")
        LOGGER.warning(
            "Input warning: The file_extension filter is not applied "
            "when you are trying to sync a single file to S3. "
            "The --extension <extension> argument is only compatible when "
            "performing a --recursive directory sync."
        )



def sync_files(
    s3_client: any,
    local_path: str,
    file_extensions: [str],
    s3_url: str,
    recursive: bool,
    delete: bool,
    metadata_to_check: MetadataToCheck,
):
    """
    Sync files using the S3 client from the local_path, matching the local_glob
    to the specific s3_url.

    Args:
        s3_client (Boto3.Client): The Boto3 S3 Client to interact with when
            a file needs to be deleted.

        local_path (str): The local path where the source files are stored.

        file_extensions ([str]): The extensions to search for files inside a
            specific path. For example, [".yml", ".yaml"] will return all
            YAML files, including those in sub directories.

        s3_url (str): The S3 URL to use, for example
            S3://bucket/specific/prefix.

        recursive (bool): Whether to search the source directory recursively
            or not.

        delete (bool): Whether to delete stale objects from the S3 bucket if
            the source file no longer exists.

        metadata_to_check (MetadataToCheck): The metadata that needs to be
            applied all the time and upon upload only.
    """
    s3_url_details = urlparse(s3_url)
    s3_bucket = s3_url_details.netloc
    s3_prefix = clean_s3_prefix(str(s3_url_details.path))

    ensure_valid_input(
        local_path,
        file_extensions,
        s3_url,
        s3_bucket,
        s3_prefix,
        recursive,
    )

    local_files = get_local_files(local_path, file_extensions, recursive)

    s3_objects = get_s3_objects(
        s3_client,
        s3_bucket,
        s3_prefix,
        file_extensions,
        recursive,
    )

    upload_changed_files(
        s3_client,
        s3_bucket,
        s3_prefix,
        local_files,
        s3_objects,
        metadata_to_check,
    )
    if delete:
        delete_stale_objects(
            s3_client,
            s3_bucket,
            s3_prefix,
            local_files,
            s3_objects,
        )


def main():  # pylint: disable=R0915
    """Main function to sync files to S3"""

    options = docopt(__doc__, version=ADF_VERSION, options_first=True)
    # In case the user asked for verbose logging, increase
    # the log level to debug.
    if options["--verbose"] > 0:
        LOGGER.setLevel(logging.DEBUG)
    if options["--verbose"] > 1:
        # Also enable DEBUG mode for other libraries, like boto3
        logging.basicConfig(level=logging.DEBUG)

    LOGGER.debug("Input arguments: %s", options)

    local_path = options.get('SOURCE_PATH')
    # Remove duplicates from file extension list if there are any
    file_extensions = list(set(options.get('--extension')))
    s3_url = options.get('DESTINATION_S3_URL')
    recursive = options.get('--recursive', False)
    delete = options.get('--delete', False)

    # Convert metadata key and value lists into a dictionary
    metadata_to_check: MetadataToCheck = {
        'always_apply': dict(map(
            lambda kv_pair: (
                kv_pair[:kv_pair.find("=")],
                kv_pair[(kv_pair.find("=") + 1):]
            ),
            options['--metadata'],
        )),
        'upon_upload_apply': dict(map(
            lambda kv_pair: (
                kv_pair[:kv_pair.find("=")],
                kv_pair[(kv_pair.find("=") + 1):]
            ),
            options['--upload-with-metadata'],
        )),
    }

    s3_client = boto3.client("s3")
    sync_files(
        s3_client,
        local_path,
        file_extensions,
        s3_url,
        recursive,
        delete,
        metadata_to_check,
    )
    LOGGER.info("All done.")


if __name__ == "__main__":
    main()
