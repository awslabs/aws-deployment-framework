# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from mock import patch
from determine_default_branch import (
    DEFAULT_FALLBACK_BRANCH,
    determine_default_branch_name,
    repo_arn_to_name,
)


class RepositoryDoesNotExistException(Exception):
    pass


def test_repo_arn_to_name():
    repo_name = "DemoRepo"
    repo_arn = f"arn:aws:codecommit:us-east-1:111111111111:{repo_name}"
    assert repo_arn_to_name(repo_arn) == repo_name


@patch('determine_default_branch.CC_CLIENT')
def test_determine_default_branch_name_default_is_defined(cc_client):
    repo_name = 'aws-deployment-framework-bootstrap'
    branch_name = 'some-branch'
    cc_client.get_repository.return_value = {
        'repositoryMetadata': {
            'defaultBranch': branch_name,
        }
    }
    assert determine_default_branch_name(repo_name) == branch_name
    cc_client.get_repository.assert_called_once_with(
        repositoryName=repo_name,
    )


@patch('determine_default_branch.CC_CLIENT')
def test_determine_default_branch_name_default_is_empty(cc_client):
    repo_name = 'aws-deployment-framework-bootstrap'
    cc_client.get_repository.return_value = {
        'repositoryMetadata': {
            'defaultBranch': '',
        }
    }
    assert determine_default_branch_name(repo_name) == DEFAULT_FALLBACK_BRANCH
    cc_client.get_repository.assert_called_once_with(
        repositoryName=repo_name,
    )


@patch('determine_default_branch.CC_CLIENT')
def test_determine_default_branch_name_default_is_not_present(cc_client):
    repo_name = 'aws-deployment-framework-bootstrap'
    cc_client.get_repository.return_value = {
        'repositoryMetadata': {}
    }
    assert determine_default_branch_name(repo_name) == DEFAULT_FALLBACK_BRANCH
    cc_client.get_repository.assert_called_once_with(
        repositoryName=repo_name,
    )


@patch('determine_default_branch.CC_CLIENT')
def test_determine_default_branch_name_repository_does_not_exist(cc_client):
    exception = RepositoryDoesNotExistException()
    repo_name = 'aws-deployment-framework-bootstrap'
    cc_client.get_repository.side_effect = exception
    cc_client.exceptions.RepositoryDoesNotExistException = (
        RepositoryDoesNotExistException
    )
    assert determine_default_branch_name(repo_name) == DEFAULT_FALLBACK_BRANCH
    cc_client.get_repository.assert_called_once_with(
        repositoryName=repo_name,
    )
