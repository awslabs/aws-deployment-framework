# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

import os
from typing import Mapping
from pathlib import Path
from copy import deepcopy
from mock import Mock, patch, call, ANY
import pytest
from base64 import b64encode
from hashlib import sha256
import tempfile
from botocore.exceptions import ClientError
from sync_to_s3 import *

# pylint: skip-file

S3_PREFIX = "s3-prefix"
CURRENT_VERSION = "This is the current version on S3".encode("utf-8")
NEW_VERSION = "This will be uploaded to S3".encode("utf-8")
CURRENT_HASH = str(b64encode(sha256(CURRENT_VERSION).digest()))
NEW_HASH = str(b64encode(sha256(NEW_VERSION).digest()))
UPLOAD_PREVIOUS_METADATA = {
    "execution_id": "a-b-c-d",
}
UPLOAD_NEW_METADATA = {
    "execution_id": "b-c-d-e",
}
PREVIOUS_METADATA = {
    "adf_version": "x.y.z",
    "another_key": "and_its_value",
}
CURRENT_METADATA = {
    "adf_version": "x.y.z+1",
    "another_key": "and_its_value",
}
IRRELEVANT_METADATA = {
    "irrelevant_metadata": "some irrelevant value",
    "another_irrelevant_key": "and-value",
}

EXAMPLE_LOCAL_FILES: Mapping[str, LocalFileData] = {
    "first-file.yml": {
        "key": "first-file.yml",
        "file_path": "/full/path/first-file.yml",
        "sha256_hash": CURRENT_HASH,
    },
    "second-file.yaml": {
        "key": "second-file.yaml",
        "file_path": "/full/path/second-file.yaml",
        "sha256_hash": CURRENT_HASH,
    },
    "needs-new-metadata-file.yaml": {
        "key": "needs-new-metadata-file.yaml",
        "file_path": "/full/path/needs-new-metadata-file.yaml",
        "sha256_hash": CURRENT_HASH,
    },
    "updated-file.yml": {
        "key": "updated-file.yml",
        "file_path": "/full/path/updated-file.yml",
        "sha256_hash": NEW_HASH,
    },
    "missing-file.yml": {
        "key": "missing-file.yml",
        "file_path": "/full/path/missing-file.yml",
        "sha256_hash": NEW_HASH,
    },
}
EXAMPLE_S3_OBJECTS: Mapping[str, S3ObjectData] = {
    "first-file.yml": {
        "key": f"{S3_PREFIX}/first-file.yml",
        "metadata": {
            **CURRENT_METADATA,
            **UPLOAD_PREVIOUS_METADATA,
            **IRRELEVANT_METADATA,
            "sha256_hash": CURRENT_HASH,
        }
    },
    "second-file.yaml": {
        "key": f"{S3_PREFIX}/second-file.yaml",
        "metadata": {
            **CURRENT_METADATA,
            **UPLOAD_PREVIOUS_METADATA,
            **IRRELEVANT_METADATA,
            "sha256_hash": CURRENT_HASH,
        }
    },
    "needs-new-metadata-file.yaml": {
        "key": f"{S3_PREFIX}/needs-new-metadata-file.yaml",
        "metadata": {
            **PREVIOUS_METADATA,
            **UPLOAD_PREVIOUS_METADATA,
            **IRRELEVANT_METADATA,
            "sha256_hash": CURRENT_HASH,
        }
    },
    "updated-file.yml": {
        "key": f"{S3_PREFIX}/updated-file.yml",
        "metadata": {
            **CURRENT_METADATA,
            **UPLOAD_PREVIOUS_METADATA,
            **IRRELEVANT_METADATA,
            "sha256_hash": CURRENT_HASH,
        }
    },
    "stale-file.yml": {
        "key": f"{S3_PREFIX}/stale-file.yml",
        "metadata": {
            **PREVIOUS_METADATA,
            **UPLOAD_PREVIOUS_METADATA,
            **IRRELEVANT_METADATA,
            "sha256_hash": CURRENT_HASH,
        }
    },
}


@patch("sync_to_s3.get_full_local_path")
def test_get_local_files_empty_directory(get_full_local_path):
    file_extensions = [".yml"]
    with tempfile.TemporaryDirectory() as directory_path:
        get_full_local_path.return_value = Path(directory_path)

        assert get_local_files(
            directory_path,
            file_extensions,
            recursive=True,
        ) == {}

        get_full_local_path.assert_called_once_with(directory_path)


@patch("sync_to_s3.get_full_local_path")
def test_get_local_files_non_recursive_missing_file(get_full_local_path):
    with tempfile.TemporaryDirectory() as directory_path:
        local_path = Path(directory_path) / "missing-file.yml"
        get_full_local_path.return_value = local_path

        assert get_local_files(
            str(local_path),
            file_extensions=[],
            recursive=False,
        ) == {}

        get_full_local_path.assert_called_once_with(str(local_path))


@patch("sync_to_s3.get_full_local_path")
def test_get_local_files_recursive(get_full_local_path):
    file_extensions = [".yml", ".yaml"]
    example_local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    example_local_files["README.md"] = {
        "key": "README.md",
        "file_path": "/full/path/README.md",
        "sha256_hash": NEW_HASH,
    }
    example_local_files["some-other-config.json"] = {
        "key": "some-other-config.json",
        "file_path": "/full/path/some-other-config.json",
        "sha256_hash": CURRENT_HASH,
    }
    with tempfile.TemporaryDirectory() as directory_path:
        get_full_local_path.return_value = Path(directory_path)

        for file in example_local_files.values():
            tmp_file_path = Path(directory_path) / file.get("key")
            with open(tmp_file_path, "wb", buffering=0) as file_pointer:
                file["file_path"] = str(Path(directory_path) / file.get("key"))
                file_pointer.write(
                    NEW_VERSION if file.get("key") in [
                        "updated-file.yml",
                        "missing-file.yml",
                        "README.md"
                    ] else CURRENT_VERSION
                )
        return_local_files = deepcopy(example_local_files)
        del return_local_files["README.md"]
        del return_local_files["some-other-config.json"]

        assert get_local_files(
            directory_path,
            file_extensions,
            recursive=True,
        ) == return_local_files

        get_full_local_path.assert_called_once_with(directory_path)


@patch("sync_to_s3.get_full_local_path")
def test_get_local_files_recursive_any(get_full_local_path):
    file_extensions = []
    example_local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    example_local_files["README.md"] = {
        "key": "README.md",
        "file_path": "/full/path/README.md",
        "sha256_hash": NEW_HASH,
    }
    example_local_files["some-other-config.json"] = {
        "key": "some-other-config.json",
        "file_path": "/full/path/some-other-config.json",
        "sha256_hash": CURRENT_HASH,
    }
    with tempfile.TemporaryDirectory() as directory_path:
        get_full_local_path.return_value = Path(directory_path)

        for file in example_local_files.values():
            tmp_file_path = Path(directory_path) / file.get("key")
            with open(tmp_file_path, "wb", buffering=0) as file_pointer:
                file["file_path"] = str(Path(directory_path) / file.get("key"))
                file_pointer.write(
                    NEW_VERSION if file.get("key") in [
                        "updated-file.yml",
                        "missing-file.yml",
                        "README.md"
                    ] else CURRENT_VERSION
                )

        assert get_local_files(
            directory_path,
            file_extensions,
            recursive=True,
        ) == example_local_files

        get_full_local_path.assert_called_once_with(directory_path)


@patch("sync_to_s3.get_full_local_path")
def test_get_local_files_recursive_unrelated_only(get_full_local_path):
    file_extensions = [".xml"]
    example_local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    with tempfile.TemporaryDirectory() as directory_path:
        get_full_local_path.return_value = Path(directory_path)

        for file in example_local_files.values():
            tmp_file_path = Path(directory_path) / file.get("key")
            with open(tmp_file_path, "wb", buffering=0) as file_pointer:
                file["file_path"] = str(Path(directory_path) / file.get("key"))
                file_pointer.write(
                    NEW_VERSION if file.get("key") in [
                        "updated-file.yml",
                        "missing-file.yml",
                    ] else CURRENT_VERSION
                )

        assert get_local_files(
            directory_path,
            file_extensions,
            recursive=True,
        ) == {}

        get_full_local_path.assert_called_once_with(directory_path)


@patch("sync_to_s3.get_full_local_path")
def test_get_local_files_recursive_no_filter(get_full_local_path):
    file_extensions = []
    example_local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    example_local_files["README.md"] = {
        "key": "README.md",
        "file_path": "/full/path/README.md",
        "sha256_hash": CURRENT_HASH,
    }
    example_local_files["some-other-config.json"] = {
        "key": "some-other-config.json",
        "file_path": "/full/path/some-other-config.json",
        "sha256_hash": CURRENT_HASH,
    }
    with tempfile.TemporaryDirectory() as directory_path:
        get_full_local_path.return_value = Path(directory_path)

        for file in example_local_files.values():
            tmp_file_path = Path(directory_path) / file.get("key")
            with open(tmp_file_path, "wb", buffering=0) as file_pointer:
                file["file_path"] = str(Path(directory_path) / file.get("key"))
                file_pointer.write(
                    NEW_VERSION if file.get("key") in [
                        "updated-file.yml",
                        "missing-file.yml",
                    ] else CURRENT_VERSION
                )

        assert get_local_files(
            directory_path,
            file_extensions,
            recursive=True,
        ) == example_local_files

        get_full_local_path.assert_called_once_with(directory_path)


@patch("sync_to_s3.get_full_local_path")
def test_get_local_file_non_recursive(get_full_local_path):
    example_local_files = {}
    file_name = "updated-file.yml"
    example_local_files[NON_RECURSIVE_KEY] = (
        deepcopy(EXAMPLE_LOCAL_FILES[file_name])
    )
    with tempfile.TemporaryDirectory() as directory_path:
        tmp_file_path = Path(directory_path) / file_name
        get_full_local_path.return_value = tmp_file_path

        with open(tmp_file_path, mode="wb", buffering=0) as file_pointer:
            example_local_files[NON_RECURSIVE_KEY]["file_path"] = str(
                tmp_file_path,
            )
            file_pointer.write(NEW_VERSION)

            assert get_local_files(
                file_pointer.name,
                file_extensions=[],
                recursive=False,
            ) == example_local_files

            get_full_local_path.assert_called_once_with(file_pointer.name)


def test_get_s3_objects_recursive_empty_bucket():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = S3_PREFIX
    file_extensions = [".yml"]

    paginator = Mock()
    s3_client.get_paginator.return_value = paginator
    paginator.paginate.return_value = [
        {},
    ]

    assert get_s3_objects(
        s3_client,
        s3_bucket,
        s3_prefix,
        file_extensions,
        recursive=True,
    ) == {}


def test_get_s3_objects_recursive_unrelated_files_only():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = S3_PREFIX
    file_extensions = [".yml"]

    paginator = Mock()
    s3_client.get_paginator.return_value = paginator
    paginator.paginate.return_value = [
        {
            "Contents": [
                {
                    "Key": "README.md",
                },
                {
                    "Key": "other-file.json",
                },
                {
                    "Key": "another-file.yaml",
                }
            ],
        },
    ]

    assert get_s3_objects(
        s3_client,
        s3_bucket,
        s3_prefix,
        file_extensions,
        recursive=True,
    ) == {}


def test_get_s3_objects_non_recursive_missing_object():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_object_key = f"{S3_PREFIX}/missing-file.yml"
    file_extensions = []

    s3_client.head_object.side_effect = ClientError(
        {
            "Error": {
                "Code": 404,
            },
        },
        "HeadObject",
    )

    assert get_s3_objects(
        s3_client,
        s3_bucket,
        s3_object_key,
        file_extensions,
        recursive=False,
    ) == {}


def test_get_s3_objects_without_prefix():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = ""
    example_s3_objects = dict(map(
        lambda kv: (
            kv[0],
            {
                # Remove the prefix from the key
                "key": kv[1]["key"][kv[1]["key"].find("/") + 1:],
                "metadata": kv[1]["metadata"],
            }
        ),
        deepcopy(EXAMPLE_S3_OBJECTS).items(),
    ))
    file_extensions = [".yml", ".yaml"]

    paginator = Mock()
    s3_client.get_paginator.return_value = paginator

    s3_obj_keys = list(map(
        lambda obj: {
            "Key": obj["key"],
        },
        example_s3_objects.values(),
    ))
    s3_obj_data = dict(map(
        lambda obj: (
            obj["key"],
            {
                "Key": obj["key"],
                "Metadata": obj["metadata"],
            }
        ),
        example_s3_objects.values(),
    ))
    paginator.paginate.return_value = [
        {
            "Contents": s3_obj_keys[:2],
        },
        {
            "Contents": [
                {
                    "Key": "README.md",
                },
                {
                    "Key": "other-file.json",
                }
            ],
        },
        {
            "Contents": s3_obj_keys[2:],
        },
    ]
    s3_client.head_object.side_effect = (
        lambda **kwargs: s3_obj_data[kwargs["Key"]]
    )

    assert get_s3_objects(
        s3_client,
        s3_bucket,
        s3_prefix,
        file_extensions,
        recursive=True,
    ) == example_s3_objects

    s3_client.get_paginator.assert_called_once_with("list_objects_v2")
    paginator.paginate.assert_called_once_with(
        Bucket=s3_bucket,
        Prefix="",
    )
    s3_client.head_object.assert_has_calls(
        list(map(
            lambda obj: call(
                Bucket=s3_bucket,
                Key=obj.get("key"),
            ),
            example_s3_objects.values(),
        )),
    )


def test_get_s3_objects_recursive_success():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = S3_PREFIX
    example_s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)
    file_extensions = [".yml", ".yaml"]

    paginator = Mock()
    s3_client.get_paginator.return_value = paginator

    s3_obj_keys = list(map(
        lambda obj: {
            "Key": obj["key"],
        },
        example_s3_objects.values(),
    ))
    s3_obj_data = dict(map(
        lambda obj: (
            obj["key"],
            {
                "Key": obj["key"],
                "Metadata": obj["metadata"],
            }
        ),
        example_s3_objects.values(),
    ))
    paginator.paginate.return_value = [
        {
            "Contents": s3_obj_keys[:2],
        },
        {
            "Contents": [
                {
                    "Key": "README.md",
                },
                {
                    "Key": "other-file.json",
                }
            ],
        },
        {
            "Contents": s3_obj_keys[2:],
        },
    ]
    s3_client.head_object.side_effect = (
        lambda **kwargs: s3_obj_data[kwargs["Key"]]
    )

    assert get_s3_objects(
        s3_client,
        s3_bucket,
        s3_prefix,
        file_extensions,
        recursive=True,
    ) == example_s3_objects

    s3_client.get_paginator.assert_called_once_with("list_objects_v2")
    paginator.paginate.assert_called_once_with(
        Bucket=s3_bucket,
        Prefix=f"{s3_prefix}/",
    )
    s3_client.head_object.assert_has_calls(
        list(map(
            lambda obj: call(
                Bucket=s3_bucket,
                Key=obj.get("key"),
            ),
            example_s3_objects.values(),
        )),
    )


def test_get_s3_objects_non_recursive_success():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_object_key = f"{S3_PREFIX}/first-file.yml"
    example_s3_objects = {}
    example_s3_objects[NON_RECURSIVE_KEY] = (
        deepcopy(EXAMPLE_S3_OBJECTS["first-file.yml"])
    )
    file_extensions = []

    s3_client.head_object.return_value = {
        "Key": "first-file.yml",
        "Metadata": {
            **CURRENT_METADATA,
            **UPLOAD_PREVIOUS_METADATA,
            **IRRELEVANT_METADATA,
            "sha256_hash": CURRENT_HASH,
        },
    }

    assert get_s3_objects(
        s3_client,
        s3_bucket,
        s3_object_key,
        file_extensions,
        recursive=False,
    ) == example_s3_objects

    s3_client.head_object.assert_called_once_with(
        Bucket=s3_bucket,
        Key=s3_object_key,
    )


def test_upload_changed_files_simple():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = S3_PREFIX
    force = False
    local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)
    metadata_to_check = {
        "always_apply": deepcopy(CURRENT_METADATA),
        "upon_upload_apply": {
            "execution_id": "example-id",
            "another-key": "another-value",
        }
    }

    with tempfile.NamedTemporaryFile(mode="wb", buffering=0) as file_pointer:
        file_pointer.write(CURRENT_VERSION)
        for key in local_files.keys():
            local_files[key]["file_path"] = file_pointer.name

        upload_changed_files(
            s3_client,
            s3_bucket,
            s3_prefix,
            local_files,
            s3_objects,
            metadata_to_check,
            force,
        )

        local_updated = local_files["updated-file.yml"]
        local_missing = local_files["missing-file.yml"]
        object_outdated_metadata = local_files["needs-new-metadata-file.yaml"]
        s3_client.put_object.assert_has_calls([
            call(
                Body=ANY,
                Bucket=s3_bucket,
                Key=f"{s3_prefix}/{object_outdated_metadata['key']}",
                Metadata={
                    **metadata_to_check["always_apply"],
                    **metadata_to_check["upon_upload_apply"],
                    "sha256_hash": object_outdated_metadata["sha256_hash"],
                }
            ),
            call(
                Body=ANY,
                Bucket=s3_bucket,
                Key=f"{s3_prefix}/{local_updated['key']}",
                Metadata={
                    **metadata_to_check["always_apply"],
                    **metadata_to_check["upon_upload_apply"],
                    "sha256_hash": local_updated["sha256_hash"],
                }
            ),
            call(
                Body=ANY,
                Bucket=s3_bucket,
                Key=f"{s3_prefix}/{local_missing['key']}",
                Metadata={
                    **metadata_to_check["always_apply"],
                    **metadata_to_check["upon_upload_apply"],
                    "sha256_hash": local_missing["sha256_hash"],
                }
            ),
        ])
        assert s3_client.put_object.call_count == 3


def test_upload_changed_files_no_updates():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = S3_PREFIX
    force = False
    local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    del local_files["updated-file.yml"]
    del local_files["missing-file.yml"]
    del local_files["needs-new-metadata-file.yaml"]
    s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)

    for obj in s3_objects.values():
        for irrelevant_key in IRRELEVANT_METADATA.keys():
            obj["metadata"][irrelevant_key] = "some-different-value"

    with tempfile.NamedTemporaryFile(mode="wb", buffering=0) as file_pointer:
        file_pointer.write(CURRENT_VERSION)
        for key in local_files.keys():
            local_files[key]["file_path"] = file_pointer.name

        upload_changed_files(
            s3_client,
            s3_bucket,
            s3_prefix,
            local_files,
            s3_objects,
            metadata_to_check={
                "always_apply": {},
                "upon_upload_apply": {},
            },
            force=force,
        )

        s3_client.put_object.assert_not_called()


def test_upload_changed_files_no_updates_forced():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = S3_PREFIX
    force = True
    local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    del local_files["updated-file.yml"]
    del local_files["missing-file.yml"]
    del local_files["needs-new-metadata-file.yaml"]
    s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)

    for obj in s3_objects.values():
        for irrelevant_key in IRRELEVANT_METADATA.keys():
            obj["metadata"][irrelevant_key] = "some-different-value"

    with tempfile.NamedTemporaryFile(mode="wb", buffering=0) as file_pointer:
        file_pointer.write(CURRENT_VERSION)
        for key in local_files.keys():
            local_files[key]["file_path"] = file_pointer.name

        upload_changed_files(
            s3_client,
            s3_bucket,
            s3_prefix,
            local_files,
            s3_objects,
            metadata_to_check={
                "always_apply": {},
                "upon_upload_apply": {},
            },
            force=force,
        )

        first_file = local_files["first-file.yml"]
        second_file = local_files["second-file.yaml"]
        s3_client.put_object.assert_has_calls([
            call(
                Body=ANY,
                Bucket=s3_bucket,
                Key=f"{s3_prefix}/{first_file['key']}",
                Metadata={
                    "sha256_hash": first_file["sha256_hash"],
                }
            ),
            call(
                Body=ANY,
                Bucket=s3_bucket,
                Key=f"{s3_prefix}/{second_file['key']}",
                Metadata={
                    "sha256_hash": second_file["sha256_hash"],
                }
            ),
        ])
        assert s3_client.put_object.call_count == 2


def test_upload_changed_files_single_file():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = "missing-file.yml"
    force = False
    s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)
    metadata_to_check = {
        "always_apply": deepcopy(CURRENT_METADATA),
        "upon_upload_apply": deepcopy(UPLOAD_NEW_METADATA),
    }

    with tempfile.NamedTemporaryFile(mode="wb", buffering=0) as file_pointer:
        file_pointer.write(CURRENT_VERSION)
        local_files = {
            "missing-file.yml": {
                "key": s3_prefix,
                "file_path": file_pointer.name,
                "sha256_hash": CURRENT_HASH,
            },
        }

        upload_changed_files(
            s3_client,
            s3_bucket,
            s3_prefix,
            local_files,
            s3_objects,
            metadata_to_check,
            force,
        )

        local_missing = local_files["missing-file.yml"]
        s3_client.put_object.assert_has_calls([
            call(
                Body=ANY,
                Bucket=s3_bucket,
                Key=f"{local_missing['key']}",
                Metadata={
                    **metadata_to_check["always_apply"],
                    **metadata_to_check["upon_upload_apply"],
                    "sha256_hash": local_missing["sha256_hash"],
                }
            ),
        ])
        assert s3_client.put_object.call_count == 1


def test_upload_changed_files_single_file_no_update():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = "first-file.yml"
    force = False
    s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)
    metadata_to_check = {
        "always_apply": deepcopy(CURRENT_METADATA),
        "upon_upload_apply": deepcopy(UPLOAD_NEW_METADATA),
    }

    for obj in s3_objects.values():
        for irrelevant_key in IRRELEVANT_METADATA.keys():
            obj["metadata"][irrelevant_key] = "some-different-value"

    with tempfile.NamedTemporaryFile(mode="wb", buffering=0) as file_pointer:
        file_pointer.write(CURRENT_VERSION)
        local_files = {
            "first-file.yml": {
                "key": s3_prefix,
                "file_path": file_pointer.name,
                "sha256_hash": CURRENT_HASH,
            },
        }

        upload_changed_files(
            s3_client,
            s3_bucket,
            s3_prefix,
            local_files,
            s3_objects,
            metadata_to_check,
            force,
        )

        s3_client.put_object.assert_not_called()


def test_upload_changed_files_single_file_no_update_forced():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = "first-file.yml"
    force = True
    s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)
    metadata_to_check = {
        "always_apply": deepcopy(CURRENT_METADATA),
        "upon_upload_apply": deepcopy(UPLOAD_NEW_METADATA),
    }

    for obj in s3_objects.values():
        for irrelevant_key in IRRELEVANT_METADATA.keys():
            obj["metadata"][irrelevant_key] = "some-different-value"

    with tempfile.NamedTemporaryFile(mode="wb", buffering=0) as file_pointer:
        file_pointer.write(CURRENT_VERSION)
        local_files = {
            "first-file.yml": {
                "key": s3_prefix,
                "file_path": file_pointer.name,
                "sha256_hash": CURRENT_HASH,
            },
        }

        upload_changed_files(
            s3_client,
            s3_bucket,
            s3_prefix,
            local_files,
            s3_objects,
            metadata_to_check,
            force,
        )

        first_file = local_files["first-file.yml"]
        s3_client.put_object.assert_has_calls([
            call(
                Body=ANY,
                Bucket=s3_bucket,
                Key=f"{first_file['key']}",
                Metadata={
                    **metadata_to_check["always_apply"],
                    **metadata_to_check["upon_upload_apply"],
                    "sha256_hash": first_file["sha256_hash"],
                }
            ),
        ])
        assert s3_client.put_object.call_count == 1


def test_delete_stale_objects_simple():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = S3_PREFIX
    local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)

    delete_stale_objects(
        s3_client,
        s3_bucket,
        s3_prefix,
        local_files,
        s3_objects,
    )

    s3_client.delete_objects.assert_called_once_with(
        Bucket=s3_bucket,
        Delete={
            "Objects": [{
                "Key": s3_objects.get("stale-file.yml").get("key"),
            }],
        },
    )


def test_delete_stale_single_object():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = "stale-file.yml"
    local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    s3_objects = {
        "stale-file.yml": {
            "key": s3_prefix,
            "sha256_hash": CURRENT_HASH,
        },
    }

    delete_stale_objects(
        s3_client,
        s3_bucket,
        s3_prefix,
        local_files,
        s3_objects,
    )

    s3_client.delete_objects.assert_called_once_with(
        Bucket=s3_bucket,
        Delete={
            "Objects": [{
                "Key": s3_prefix,
            }],
        },
    )


def test_delete_stale_objects_no_stale_objects():
    s3_client = Mock()
    s3_bucket = "your-bucket"
    s3_prefix = S3_PREFIX
    local_files = deepcopy(EXAMPLE_LOCAL_FILES)
    s3_objects = deepcopy(EXAMPLE_S3_OBJECTS)
    del s3_objects["stale-file.yml"]

    delete_stale_objects(
        s3_client,
        s3_bucket,
        s3_prefix,
        local_files,
        s3_objects,
    )

    s3_client.delete_objects.assert_not_called()


def test_clean_s3_prefix():
    assert clean_s3_prefix("some-path") == "some-path"
    assert clean_s3_prefix("/some-path") == "some-path"
    assert clean_s3_prefix("some-path/") == "some-path"
    assert clean_s3_prefix("/some-path") == "some-path"
    assert clean_s3_prefix("") == ""


def test_full_local_path_relative_to_cwd():
    local_path = "local/path"
    here = Path(os.getcwd())
    assert (here / local_path) == get_full_local_path(local_path)


def test_full_local_path_absolute_path():
    absolute_path = "/absolute/path"
    assert Path(absolute_path) == get_full_local_path(absolute_path)


def test_convert_to_s3_key():
    # Local key == s3_prefix
    assert convert_to_s3_key("a.yml", "a.yml") == "a.yml"

    # S3 prefix is set
    assert convert_to_s3_key("some-path", "prefix") == "prefix/some-path"

    # S3 prefix is set and local key matches NON_RECURSIVE_KEY
    assert convert_to_s3_key(NON_RECURSIVE_KEY, "full-s3-obj") == "full-s3-obj"

    # S3 prefix is Non
    assert convert_to_s3_key("some-path", "") == "some-path"


def test_convert_to_local_key():
    # Local key == s3_prefix
    assert convert_to_local_key("a.yml", "a.yml") == "a.yml"

    # S3 prefix is set local
    assert convert_to_local_key("prefix/some-path", "prefix") == "some-path"

    # S3 prefix is Nonlocal
    assert convert_to_local_key("some-path", "") == "some-path"


@patch("sys.exit")
def test_ensure_valid_input_no_local_path(sys_exit):
    s3_bucket = "your-bucket"
    s3_prefix = ""
    s3_url = f"s3://{s3_bucket}/{s3_prefix}"

    test_exit_message = "Would have exited with exit code 1"
    sys_exit.side_effect = Exception(test_exit_message)

    with pytest.raises(Exception) as exc_info:
        ensure_valid_input(
            local_path="",
            file_extensions=[".yml"],
            s3_url=s3_url,
            s3_bucket=s3_bucket,
            s3_prefix=s3_prefix,
            recursive=False,
        )
    error_message = str(exc_info.value)
    assert error_message.find(test_exit_message) >= 0

    sys_exit.assert_called_once_with(1)


@patch("sys.exit")
def test_ensure_valid_input_no_destination_s3_url(sys_exit):
    test_exit_message = "Would have exited with exit code 2"
    sys_exit.side_effect = Exception(test_exit_message)

    with pytest.raises(Exception) as exc_info:
        ensure_valid_input(
            local_path="/tmp/some-path",
            file_extensions=[".yml"],
            s3_url="",
            s3_bucket="",
            s3_prefix="",
            recursive=False,
        )
    error_message = str(exc_info.value)
    assert error_message.find(test_exit_message) >= 0

    sys_exit.assert_called_once_with(2)


@patch("sys.exit")
def test_ensure_valid_input_non_recursive_and_no_s3_prefix(sys_exit):
    s3_bucket = "your-bucket"
    s3_prefix = ""
    s3_url = f"s3://{s3_bucket}/{s3_prefix}"

    test_exit_message = "Would have exited with exit code 3"
    sys_exit.side_effect = Exception(test_exit_message)

    with pytest.raises(Exception) as exc_info:
        ensure_valid_input(
            local_path="/tmp/some-path",
            file_extensions=[".yml"],
            s3_url=s3_url,
            s3_bucket=s3_bucket,
            s3_prefix=s3_prefix,
            recursive=False,
        )
    error_message = str(exc_info.value)
    assert error_message.find(test_exit_message) >= 0

    sys_exit.assert_called_once_with(3)


@patch("sys.exit")
def test_ensure_valid_input_recursive_and_path_does_not_exist(sys_exit):
    s3_bucket = "your-bucket"
    s3_prefix = ""
    s3_url = f"s3://{s3_bucket}/{s3_prefix}"

    test_exit_message = "Would have exited with exit code 4"
    sys_exit.side_effect = Exception(test_exit_message)

    with pytest.raises(Exception) as exc_info:
        ensure_valid_input(
            local_path="/tmp/some-path",
            file_extensions=[".yml"],
            s3_url=s3_url,
            s3_bucket=s3_bucket,
            s3_prefix=s3_prefix,
            recursive=True,
        )
    error_message = str(exc_info.value)
    assert error_message.find(test_exit_message) >= 0

    sys_exit.assert_called_once_with(4)


@patch("sys.exit")
def test_ensure_valid_input_not_recursive_and_path_is_a_dir(sys_exit):
    s3_bucket = "your-bucket"
    s3_prefix = "a-prefix.yml"
    s3_url = f"s3://{s3_bucket}/{s3_prefix}"

    test_exit_message = "Would have exited with exit code 5"
    sys_exit.side_effect = Exception(test_exit_message)

    with tempfile.TemporaryDirectory() as directory_path:
        with pytest.raises(Exception) as exc_info:
            ensure_valid_input(
                local_path=directory_path,
                file_extensions=[".yml"],
                s3_url=s3_url,
                s3_bucket=s3_bucket,
                s3_prefix=s3_prefix,
                recursive=False,
            )
        error_message = str(exc_info.value)
        assert error_message.find(test_exit_message) >= 0

    sys_exit.assert_called_once_with(5)


@patch("sync_to_s3.delete_stale_objects")
@patch("sync_to_s3.upload_changed_files")
@patch("sync_to_s3.get_s3_objects")
@patch("sync_to_s3.get_local_files")
@patch("sync_to_s3.ensure_valid_input")
def test_sync_files_recursive_delete(
    ensure_valid_input,
    get_local_files,
    get_s3_objects,
    upload_files,
    delete_stale,
):
    s3_client = Mock()
    local_path = "/tmp/some-path"
    file_extensions = [".yml"]
    s3_bucket = "your-bucket"
    s3_prefix = "your-prefix"
    s3_url = f"s3://{s3_bucket}/{s3_prefix}"
    recursive = True
    delete = True
    force = True
    metadata_to_check = {
        "always_apply": deepcopy(CURRENT_METADATA),
        "upon_upload_apply": deepcopy(UPLOAD_PREVIOUS_METADATA),
    }

    local_files = Mock()
    s3_objects = Mock()
    get_local_files.return_value = local_files
    get_s3_objects.return_value = s3_objects

    sync_files(
        s3_client,
        local_path,
        file_extensions,
        s3_url,
        recursive,
        delete,
        metadata_to_check,
        force,
    )

    get_local_files.assert_called_once_with(
        local_path,
        file_extensions,
        recursive,
    )
    get_s3_objects.assert_called_once_with(
        s3_client,
        s3_bucket,
        s3_prefix,
        file_extensions,
        recursive,
    )
    upload_files.assert_called_once_with(
        s3_client,
        s3_bucket,
        s3_prefix,
        local_files,
        s3_objects,
        metadata_to_check,
        force,
    )
    delete_stale.assert_called_once_with(
        s3_client,
        s3_bucket,
        s3_prefix,
        local_files,
        s3_objects,
    )


@patch("sync_to_s3.delete_stale_objects")
@patch("sync_to_s3.upload_changed_files")
@patch("sync_to_s3.get_s3_objects")
@patch("sync_to_s3.get_local_files")
@patch("sync_to_s3.ensure_valid_input")
def test_sync_files_recursive_no_delete(
    ensure_valid_input,
    get_local_files,
    get_s3_objects,
    upload_files,
    delete_stale,
):
    s3_client = Mock()
    local_path = "/tmp/some-path"
    file_extensions = [".yml"]
    s3_bucket = "your-bucket"
    s3_prefix = "your-prefix"
    s3_url = f"s3://{s3_bucket}/{s3_prefix}"
    recursive = True
    delete = False
    force = False
    metadata_to_check = {
        "always_apply": deepcopy(CURRENT_METADATA),
        "upon_upload_apply": deepcopy(UPLOAD_PREVIOUS_METADATA),
    }

    local_files = Mock()
    s3_objects = Mock()
    get_local_files.return_value = local_files
    get_s3_objects.return_value = s3_objects

    sync_files(
        s3_client,
        local_path,
        file_extensions,
        s3_url,
        recursive,
        delete,
        metadata_to_check,
        force,
    )

    ensure_valid_input.assert_called_once_with(
        local_path,
        file_extensions,
        s3_url,
        s3_bucket,
        s3_prefix,
        recursive,
    )
    get_local_files.assert_called_once_with(
        local_path,
        file_extensions,
        recursive,
    )
    get_s3_objects.assert_called_once_with(
        s3_client,
        s3_bucket,
        s3_prefix,
        file_extensions,
        recursive,
    )
    upload_files.assert_called_once_with(
        s3_client,
        s3_bucket,
        s3_prefix,
        local_files,
        s3_objects,
        metadata_to_check,
        force,
    )
    delete_stale.assert_not_called()
