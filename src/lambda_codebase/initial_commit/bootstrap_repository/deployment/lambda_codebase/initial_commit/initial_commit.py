"""
The Initial Commit main that is called when ADF is installed to commit the initial pipelines repository content
"""

from typing import Mapping, Optional, Union, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import os
import boto3
import jinja2
from cfn_custom_resource import (  # pylint: disable=unused-import
    lambda_handler,
    create,
    update,
    delete,
)


PhysicalResourceId = str
Data = Mapping[str, str]

HERE = Path(__file__).parent
NOT_YET_CREATED = "NOT_YET_CREATED"
CC_CLIENT = boto3.client("codecommit")

PR_DESCRIPTION = """ADF Version {0} from https://github.com/awslabs/aws-deployment-framework

This PR was automatically created when you deployed version {0} of the AWS Deployment Framework through the Serverless Application Repository.

Review this PR to understand what changes will be made to your pipelines repository. If you also made changes to the repository yourself, you might have to resolve merge conflicts before you can merge this PR.

Merge this PR to complete the deployment of the version {0} of the AWS Deployment Framework.
"""


@dataclass
class CustomResourceProperties:
    ServiceToken: str
    RepositoryArn: str
    DirectoryName: str
    Version: str
    DeploymentAccountRegion: Optional[str] = None
    TargetRegions: Optional[List[str]] = None
    NotificationEndpoint: Optional[str] = None
    NotificationEndpointType: Optional[str] = None

    def __post_init__(self):
        if self.NotificationEndpoint:
            self.NotificationEndpointType = (
                "email"
                if "@"
                in self.NotificationEndpoint  # pylint:disable=unsupported-membership-test
                else "slack"
            )


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


class FileMode(Enum):
    EXECUTABLE = "EXECUTABLE"
    NORMAL = "NORMAL"
    SYMLINK = "SYMLINK"


@dataclass
class FileToCommit:
    filePath: str
    fileMode: FileMode
    fileContent: bytes

    def as_dict(self) -> Dict[str, Union[str, bytes]]:
        return {
            "filePath": self.filePath,
            "fileMode": self.fileMode.value,
            "fileContent": self.fileContent,
        }

@dataclass
class FileToDelete:
    filePath: str

    def as_dict(self) -> Dict[str, Union[str, bytes]]:
        return {
            "filePath": self.filePath
        }

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

def chunks(l, n):
    n = max(1, n)
    return (l[i:i+n] for i in range(0, len(l), n))

@create()
def create_(event: Mapping[str, Any], _context: Any) -> Tuple[Union[None, PhysicalResourceId], Data]:
    create_event = CreateEvent(**event)
    repo_name = repo_arn_to_name(create_event.ResourceProperties.RepositoryArn)
    directory = create_event.ResourceProperties.DirectoryName
    files_to_commit = get_files_to_commit(directory)
    try:
        commit_id = CC_CLIENT.get_branch(
            repositoryName=repo_name,
            branchName="master",
        )["branch"]["commitId"]
        CC_CLIENT.create_branch(
            repositoryName=repo_name,
            branchName=create_event.ResourceProperties.Version,
            commitId=commit_id
        )
        for index, files in enumerate(chunks([f.as_dict() for f in files_to_commit], 99)):
            CC_CLIENT.create_commit(
                repositoryName=repo_name,
                branchName=create_event.ResourceProperties.Version,
                parentCommitId=commit_id,
                authorName='ADF Update PR',
                email='adf-builders@amazon.com',
                commitMessage='ADF {0} Automated Update PR - Part {1}'.format(create_event.ResourceProperties.Version, index),
                putFiles=files
            )
        CC_CLIENT.create_pull_request(
            title='ADF {0} Automated Update PR'.format(create_event.ResourceProperties.Version),
            description=PR_DESCRIPTION.format(create_event.ResourceProperties.Version),
            targets=[
                {
                    'repositoryName': repo_name,
                    'sourceReference': create_event.ResourceProperties.Version,
                    'destinationReference': 'master'
                },
            ]
        )
        return event.get("PhysicalResourceId"), {}
    except (CC_CLIENT.exceptions.FileEntryRequiredException, CC_CLIENT.exceptions.NoChangeException):
        CC_CLIENT.delete_branch(
            repositoryName=repo_name,
            branchName=create_event.ResourceProperties.Version
        )
        return event.get("PhysicalResourceId"), {}
    except CC_CLIENT.exceptions.BranchDoesNotExistException:
        files_to_commit = get_files_to_commit(directory)
        if directory == "bootstrap_repository":
            adf_config = create_adf_config_file(create_event.ResourceProperties)
            files_to_commit.append(adf_config)
        latest_commit_id = 0
        for index, files in enumerate(chunks([f.as_dict() for f in files_to_commit], 99)):
            commit_args = {
                "repositoryName": repo_name,
                "branchName": "master",
                "authorName": "AWS ADF Builders Team",
                "email": "adf-builders@amazon.com",
                "commitMessage": "Initial automated commit - Part {0}".format(index),
                "putFiles": files
            }
            if index == 0:
                commit_response = CC_CLIENT.create_commit(**commit_args)
                latest_commit_id = commit_response["commitId"]
            else:
                commit_args["parentCommitId"] = latest_commit_id
                commit_response = CC_CLIENT.create_commit(**commit_args)
                latest_commit_id = commit_response["commitId"]

        return commit_response["commitId"], {}

@update()
def update_(event: Mapping[str, Any], _context: Any, create_pr=False) -> Tuple[PhysicalResourceId, Data]: #pylint: disable=R0915
    update_event = UpdateEvent(**event)
    directory = update_event.ResourceProperties.DirectoryName
    repo_name = repo_arn_to_name(update_event.ResourceProperties.RepositoryArn)
    files_to_delete = get_files_to_delete(repo_name)
    files_to_commit = get_files_to_commit(directory)
    commit_id = CC_CLIENT.get_branch(
        repositoryName=repo_name,
        branchName="master",
    )["branch"]["commitId"]
    CC_CLIENT.create_branch(
        repositoryName=repo_name,
        branchName=update_event.ResourceProperties.Version,
        commitId=commit_id
    )

    try:
        for index, files in enumerate(chunks([f.as_dict() for f in files_to_commit], 99)):
            commit_args = {
                "repositoryName": repo_name,
                "branchName": update_event.ResourceProperties.Version,
                "authorName": "AWS ADF Builders Team",
                "parentCommitId": commit_id,
                "email": "adf-builders@amazon.com",
                "commitMessage": "ADF {0} Automated Update PR - Part {1}".format(update_event.ResourceProperties.Version, index),
                "putFiles": files
            }
            if index == 0:
                commit_response = CC_CLIENT.create_commit(**commit_args)
                create_pr = True
                commit_id = commit_response["commitId"]
            else:
                commit_args["parentCommitId"] = commit_id
                commit_response = CC_CLIENT.create_commit(**commit_args)
                commit_id = commit_response["commitId"]
    except (CC_CLIENT.exceptions.FileEntryRequiredException, CC_CLIENT.exceptions.NoChangeException):
        pass
    if files_to_delete:
        try:
            for index, deletes in enumerate(chunks([f.as_dict() for f in files_to_delete], 99)):
                commit_args = {
                    "repositoryName": repo_name,
                    "branchName": update_event.ResourceProperties.Version,
                    "authorName": "AWS ADF Builders Team",
                    "parentCommitId": commit_id,
                    "email": "adf-builders@amazon.com",
                    "commitMessage": "ADF {0} Automated Update PR - Part {1}".format(update_event.ResourceProperties.Version, index),
                    "deleteFiles": deletes
                }
                if index == 0:
                    commit_response = CC_CLIENT.create_commit(**commit_args)
                    commit_id = commit_response["commitId"]
                else:
                    commit_args["parentCommitId"] = commit_id
                    commit_response = CC_CLIENT.create_commit(**commit_args)
                    commit_id = commit_response["commitId"]
        except (CC_CLIENT.exceptions.FileEntryRequiredException, CC_CLIENT.exceptions.NoChangeException):
            pass

    if create_pr or files_to_delete:
        CC_CLIENT.create_pull_request(
            title='ADF {0} Automated Update PR'.format(update_event.ResourceProperties.Version),
            description=PR_DESCRIPTION.format(update_event.ResourceProperties.Version),
            targets=[
                {
                    'repositoryName': repo_name,
                    'sourceReference': update_event.ResourceProperties.Version,
                    'destinationReference': 'master'
                },
            ]
        )
    else:
        CC_CLIENT.delete_branch(
            repositoryName=repo_name,
            branchName=update_event.ResourceProperties.Version
        )

    return event["PhysicalResourceId"], {}


@delete()
def delete_(_event, _context):
    pass


def repo_arn_to_name(repo_arn: str) -> str:
    return repo_arn.split(":")[-1]

def get_files_to_delete(repo_name: str) -> List[FileToDelete]:
    differences = CC_CLIENT.get_differences(
        repositoryName=repo_name,
        afterCommitSpecifier='HEAD'
    )['differences']

    file_paths = [
        Path(file['afterBlob']['path'])
        for file in differences
        if 'adfconfig.yml' not in file['afterBlob']['path']
        and 'scp.json' not in file['afterBlob']['path']
        and 'global.yml' not in file['afterBlob']['path']
        and 'regional.yml' not in file['afterBlob']['path']
        and file['afterBlob']['path'] != 'deployment_map.yml'
    ]
    # 31: trimming off /var/task/pipelines_repository so we can compare correctly
    blobs = [str(filename)[31:] for filename in Path('/var/task/pipelines_repository/').rglob('*')]
    return [
        FileToDelete(
            str(entry)
        )
        for entry in file_paths
        if str(entry) not in blobs
        and not entry.is_dir()
    ]

def get_files_to_commit(directoryName: str) -> List[FileToCommit]:
    path = HERE / directoryName

    return [
        FileToCommit(
            str(get_relative_name(entry, directoryName)),
            FileMode.NORMAL if not os.access(entry, os.X_OK) else FileMode.EXECUTABLE,
            entry.read_bytes(),
        )
        for entry in path.glob("**/*")
        if not entry.is_dir()
    ]


def get_relative_name(path: Path, directoryName: str) -> Path:
    """
    Search for the last occurance of <directoryName> in <path> and return only the trailing part of <path>

    >>> get_relative_name(Path('/foo/test/bar/test/xyz/abc.py') ,'test')
    Path('xyz/abc.py')
    """
    index = list(reversed(path.parts)).index(directoryName)
    return Path(*path.parts[-index:])


def create_adf_config_file(props: CustomResourceProperties) -> FileToCommit:
    template = HERE / "adfconfig.yml.j2"
    adf_config = (
        jinja2.Template(template.read_text(), undefined=jinja2.StrictUndefined)
        .render(vars(props))
        .encode()
    )

    with open("/tmp/adfconfig.yml", "wb") as f:
        f.write(adf_config)
    return FileToCommit("adfconfig.yml", FileMode.NORMAL, adf_config)
