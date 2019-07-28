"""
The Initial Commit main that is called when ADF is installed to commit the initial bootstrap repository content
"""

from typing import Mapping, Optional, Union, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import os
import boto3
import jinja2
from cfn_custom_resource import ( # pylint: disable=unused-import
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

Review this PR to understand what changes will be made to your bootstrapping repository. If you also made changes to the repository yourself, you might have to resolve merge conflicts before you can merge this PR.

Merge this PR to complete the deployment of the version {0} of the AWS Deployment Framework.
"""
@dataclass
class CustomResourceProperties:
    ServiceToken: str
    RepositoryArn: str
    DirectoryName: str
    Version: str
    CrossAccountAccessRole: Optional[str] = None
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
            **self.ResourceProperties # pylint: disable=not-a-mapping
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
            **self.ResourceProperties # pylint: disable=not-a-mapping
        )
        self.OldResourceProperties = CustomResourceProperties(
            **self.OldResourceProperties # pylint: disable=not-a-mapping
        )

def generate_create_branch_input(event, repo_name, commit_id):
    return {
        "repositoryName": repo_name,
        "branchName": event.ResourceProperties.Version,
        "commitId": commit_id
    }

def generate_delete_branch_input(event, repo_name):
    return {
        "repositoryName": repo_name,
        "branchName": event.ResourceProperties.Version
    }

def chunks(list_to_chunk, number_to_chunk_into):
    number_of_chunks = max(1, number_to_chunk_into)
    return (list_to_chunk[item:item + number_of_chunks] for item in range(0, len(list_to_chunk), number_of_chunks))

def generate_pull_request_input(event, repo_name):
    return {
        "title": 'ADF {0} Automated Update PR'.format(event.ResourceProperties.Version),
        "description": PR_DESCRIPTION.format(event.ResourceProperties.Version),
        "targets": [
            {
                'repositoryName': repo_name,
                'sourceReference': event.ResourceProperties.Version,
                'destinationReference': 'master'
            },
        ]
    }

def generate_commit_input(repo_name, index, branch="master", parent_commit_id=None, puts=None, deletes=None):
    output = {
        "repositoryName": repo_name,
        "branchName": branch,
        "authorName": "AWS ADF Builders Team",
        "email": "adf-builders@amazon.com",
        "commitMessage": "Automated Commit - {0} Part {1}".format("Delete" if deletes else "Create", index),
        "putFiles": puts if puts else [],
        "deleteFiles": deletes if deletes else []
    }
    if parent_commit_id:
        output["parentCommitId"] = parent_commit_id
    return output

@create()
def create_(event: Mapping[str, Any], _context: Any) -> Tuple[Union[None, PhysicalResourceId], Data]:
    create_event = CreateEvent(**event)
    repo_name = repo_arn_to_name(create_event.ResourceProperties.RepositoryArn)
    directory = create_event.ResourceProperties.DirectoryName
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
        # CodeCommit only allows 100 files per commit, so we chunk them up here
        for index, files in enumerate(chunks([f.as_dict() for f in get_files_to_commit(directory)], 99)):
            if index == 0:
                commit_id = CC_CLIENT.create_commit(
                    **generate_commit_input(repo_name, index, puts=files)
                )["commitId"]
            else:
                commit_id = CC_CLIENT.create_commit(
                    **generate_commit_input(repo_name, index, puts=files, parent_commit_id=commit_id)
                )["commitId"]

        CC_CLIENT.create_pull_request(
            **generate_pull_request_input(create_event, repo_name)
        )
        return event.get("PhysicalResourceId"), {}

    except (CC_CLIENT.exceptions.FileEntryRequiredException, CC_CLIENT.exceptions.NoChangeException):
        CC_CLIENT.delete_branch(**generate_delete_branch_input(create_event, repo_name))
        return event.get("PhysicalResourceId"), {}

    except CC_CLIENT.exceptions.BranchDoesNotExistException:
        files_to_commit = get_files_to_commit(directory)
        if directory == "bootstrap_repository":
            adf_config = create_adf_config_file(create_event.ResourceProperties)
            files_to_commit.append(adf_config)

        for index, files in enumerate(chunks([f.as_dict() for f in files_to_commit], 99)):
            if index == 0:
                commit_id = CC_CLIENT.create_commit(
                    **generate_commit_input(repo_name, index, puts=files)
                )["commitId"]
            else:
                commit_id = CC_CLIENT.create_commit(
                    **generate_commit_input(repo_name, index, puts=files, parent_commit_id=commit_id)
                )["commitId"]

        return commit_id, {}

@update()
def update_(event: Mapping[str, Any], _context: Any, create_pr=False) -> Tuple[PhysicalResourceId, Data]: #pylint: disable=R0912, R0915
    update_event = UpdateEvent(**event)
    repo_name = repo_arn_to_name(update_event.ResourceProperties.RepositoryArn)
    files_to_delete = get_files_to_delete(repo_name)
    files_to_commit = get_files_to_commit(update_event.ResourceProperties.DirectoryName)

    commit_id = CC_CLIENT.get_branch(
        repositoryName=repo_name,
        branchName="master",
    )["branch"]["commitId"]
    CC_CLIENT.create_branch(
        **generate_create_branch_input(update_event, repo_name, commit_id)
    )

    if files_to_commit:
        try:
            for index, files in enumerate(chunks([f.as_dict() for f in files_to_commit], 99)):
                commit_id = CC_CLIENT.create_commit(**generate_commit_input(
                    repo_name,
                    index,
                    parent_commit_id=commit_id,
                    branch=update_event.ResourceProperties.Version,
                    puts=files))["commitId"]
                create_pr = True # If the commit above was able to be made, we want to create a PR afterwards
        except (CC_CLIENT.exceptions.FileEntryRequiredException, CC_CLIENT.exceptions.NoChangeException):
            pass
    if files_to_delete:
        try:
            for index, deletes in enumerate(chunks([f.as_dict() for f in files_to_delete], 99)):
                commit_id = CC_CLIENT.create_commit(**generate_commit_input(
                    repo_name,
                    index,
                    parent_commit_id=commit_id,
                    branch=update_event.ResourceProperties.Version,
                    deletes=deletes
                ))["commitId"]
        except (CC_CLIENT.exceptions.FileEntryRequiredException, CC_CLIENT.exceptions.NoChangeException):
            pass
    if create_pr or files_to_delete:
        CC_CLIENT.create_pull_request(**generate_pull_request_input(update_event, repo_name))
    else:
        CC_CLIENT.delete_branch(**generate_delete_branch_input(update_event, repo_name))

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
