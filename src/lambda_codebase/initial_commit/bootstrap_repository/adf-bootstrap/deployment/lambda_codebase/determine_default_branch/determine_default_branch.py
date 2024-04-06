"""
The Determine Default Branch Logic that is called when ADF is installed
or updated to determine the default branch for the given repository.
"""
from typing import Any, Mapping, TypedDict, Tuple, Union
from dataclasses import dataclass
import boto3
from cfn_custom_resource import (  # pylint: disable=unused-import
    create,
    update,
    delete,
)

# pylint: disable=invalid-name

PhysicalResourceId = str
ResponseData = TypedDict("ResponseData", {
    "DefaultBranchName": str,
})
CC_CLIENT = boto3.client("codecommit")
DEFAULT_FALLBACK_BRANCH = 'main'


@dataclass
class CustomResourceProperties:
    ServiceToken: str
    RepositoryArn: str
    Version: str


@dataclass
class Event:
    RequestType: str
    ServiceToken: str
    ResponseURL: str
    StackId: str
    RequestId: str
    ResourceType: str
    LogicalResourceId: str
    ResourceProperties: CustomResourceProperties

    def __post_init__(self):
        self.ResourceProperties = CustomResourceProperties(
            **self.ResourceProperties  # pylint: disable=not-a-mapping
        )


@dataclass
class CreateEvent(Event):
    pass


@dataclass
class UpdateEvent(Event):
    PhysicalResourceId: str
    OldResourceProperties: CustomResourceProperties

    def __post_init__(self):
        self.ResourceProperties = CustomResourceProperties(
            **self.ResourceProperties  # pylint: disable=not-a-mapping
        )
        self.OldResourceProperties = CustomResourceProperties(
            **self.OldResourceProperties  # pylint: disable=not-a-mapping
        )


def repo_arn_to_name(repo_arn: str) -> str:
    return repo_arn.split(":")[-1]


def determine_default_branch_name(repo_name) -> str:
    try:
        response = CC_CLIENT.get_repository(
            repositoryName=repo_name,
        )
        return (
            response['repositoryMetadata'].get('defaultBranch')
            or DEFAULT_FALLBACK_BRANCH
        )
    except CC_CLIENT.exceptions.RepositoryDoesNotExistException:
        return DEFAULT_FALLBACK_BRANCH


@create()
def create_(
    event: Mapping[str, Any],
    _context: Any,
) -> Tuple[Union[None, PhysicalResourceId], ResponseData]:
    create_event = CreateEvent(**event)
    repo_name = repo_arn_to_name(create_event.ResourceProperties.RepositoryArn)
    default_branch_name = determine_default_branch_name(repo_name)
    return (
        str(event.get('PhysicalResourceId')) or None,
        {
            "DefaultBranchName": default_branch_name,
        }
    )


@update()
def update_(
    event: Mapping[str, Any],
    _context: Any,
) -> Tuple[PhysicalResourceId, ResponseData]: #pylint: disable=R0912, R0915
    update_event = UpdateEvent(**event)
    repo_name = repo_arn_to_name(update_event.ResourceProperties.RepositoryArn)
    default_branch_name = determine_default_branch_name(repo_name)
    return (
        str(event.get('PhysicalResourceId')),
        {
            "DefaultBranchName": default_branch_name,
        }
    )


@delete()
def delete_(_event, _context):
    pass
