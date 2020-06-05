# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from mock import Mock, patch
from initial_commit import (
    FileToDelete,
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
]
SHOULD_DELETE_PATHS = [
    'other.txt',
    'pipeline_types/cc-cloudformation.yml.j2',
    'cc-cloudformation.yml.j2',
]


class GenericPathMocked():
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return self.path

    def is_dir(self):
        return self.path in SHOULD_NOT_DELETE_DIRS


@patch('initial_commit.Path')
@patch('initial_commit.CC_CLIENT')
def test_get_files_to_delete(cc_client, path_cls):
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
    cc_client.get_differences.return_value = {
        'differences': differences,
    }
    path_rglob_mock = Mock()
    path_rglob_mock.rglob.return_value = list(map(
        lambda path: "/var/task/bootstrap_repository/{}".format(path),
        FILES_IN_UPSTREAM_REPO,
    ))
    path_cls.side_effect = lambda path: (
        path_rglob_mock if path == '/var/task/bootstrap_repository/'
        else GenericPathMocked(path)
    )

    result = get_files_to_delete(repo_name)

    cc_client.get_differences.assert_called_once_with(
        repositoryName=repo_name,
        afterCommitSpecifier='HEAD',
    )

    path_cls.assert_called_with(
        '/var/task/bootstrap_repository/'
    )
    path_rglob_mock.rglob.assert_called_once_with('*')

    assert all(isinstance(x, FileToDelete) for x in result)

    # Extract paths from result FileToDelete objects to make querying easier
    result_paths = list(map(lambda x: x.filePath, result))

    # Should not delete JSON, YAML, and directories
    assert all(x not in result_paths for x in SHOULD_NOT_DELETE_FILES)
    assert all(x not in result_paths for x in SHOULD_NOT_DELETE_DIRS)

    # Should delete all other
    assert all(x in result_paths for x in SHOULD_DELETE_PATHS)
    assert len(result_paths) == len(SHOULD_DELETE_PATHS)
