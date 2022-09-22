# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import tempfile
from pathlib import Path
import pytest
from mock import Mock, patch
from initial_commit import (
    EXECUTABLE_FILES,
    FileMode,
    FileToDelete,
    determine_file_mode,
    get_files_to_delete,
)


FILES_IN_UPSTREAM_REPO = [
    'some.yml',
    'otherfile.txt',
    'samples/python.py',
]
FILES_ADDED_BY_USER = [
    'global.yml',
    'REGIONAL.YML',
    'regional.yml',
    'scp.json',
    'other.JSON',
    'other.yaml',
    'deployment_maps/test.yml',
]
SHOULD_NOT_DELETE_FILES = FILES_IN_UPSTREAM_REPO + FILES_ADDED_BY_USER
SHOULD_NOT_DELETE_DIRS = [
    'deployment_maps',
    'deployment',
    'samples',
]
SHOULD_DELETE_PATHS = [
    'other.txt',
    'pipeline_types/cc-cloudformation.yml.j2',
    'cc-cloudformation.yml.j2',
]
SHOULD_NOT_BE_EXECUTABLE = [
    "README.md",
    "deployment_map.yml",
]


class GenericPathMocked():
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return self.path

    def is_dir(self):
        return self.path in SHOULD_NOT_DELETE_DIRS


@patch('initial_commit.CC_CLIENT')
def test_get_files_to_delete(cc_client):
    repo_name = 'some-repo-name'
    difference_paths = (
        SHOULD_NOT_DELETE_FILES +
        SHOULD_NOT_DELETE_DIRS +
        SHOULD_DELETE_PATHS
    )
    differences = list(map(
        lambda x: {'afterBlob': {'path': x}},
        difference_paths,
    ))
    paginator = Mock()
    cc_client.get_paginator.return_value = paginator
    paginator.paginate.return_value = [
        {
            'differences': differences[:2],
        },
        {
            'differences': differences[2:],
        },
    ]
    with tempfile.TemporaryDirectory() as temp_dir_path:
        directory_path = Path(temp_dir_path)
        for dir_name in SHOULD_NOT_DELETE_DIRS:
            os.mkdir(str(directory_path / dir_name))
        for file_name in SHOULD_NOT_DELETE_FILES:
            with open(str(directory_path / file_name), "wb") as file_p:
                file_p.write("Test".encode('utf-8'))

        result = get_files_to_delete(repo_name, directory_path)

    cc_client.get_paginator.assert_called_once_with(
        'get_differences',
    )
    paginator.paginate.assert_called_once_with(
        repositoryName=repo_name,
        afterCommitSpecifier='HEAD',
    )

    assert all(isinstance(x, FileToDelete) for x in result)

    # Extract paths from result FileToDelete objects to make querying easier
    result_paths = list(map(lambda x: x.filePath, result))

    # Should not delete JSON, YAML, and directories
    assert all(x not in result_paths for x in SHOULD_NOT_DELETE_FILES)
    assert all(x not in result_paths for x in SHOULD_NOT_DELETE_DIRS)

    # Should delete all other
    assert result_paths == SHOULD_DELETE_PATHS
    assert len(result_paths) == len(SHOULD_DELETE_PATHS)

    # Extract paths from result FileToDelete objects to make querying easier
    result_paths = list(map(lambda x: x.filePath, result))

    # Should not delete JSON, YAML, and directories
    assert all(x not in result_paths for x in SHOULD_NOT_DELETE_FILES)
    assert all(x not in result_paths for x in SHOULD_NOT_DELETE_DIRS)

    # Should delete all other
    assert all(x in result_paths for x in SHOULD_DELETE_PATHS)
    assert len(result_paths) == len(SHOULD_DELETE_PATHS)


@pytest.mark.parametrize("entry", SHOULD_NOT_BE_EXECUTABLE)
def test_determine_file_mode_normal(entry):
    base_path = Path("/some/test")
    new_entry = base_path / entry
    assert determine_file_mode(
        new_entry,
        base_path,
    ) == FileMode.NORMAL


@pytest.mark.parametrize("entry", EXECUTABLE_FILES)
def test_determine_file_mode_executable(entry):
    base_path = Path("/some/test")
    new_entry = base_path / entry
    assert determine_file_mode(
        new_entry,
        base_path,
    ) == FileMode.EXECUTABLE
