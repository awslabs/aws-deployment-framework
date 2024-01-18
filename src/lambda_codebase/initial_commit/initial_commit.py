"""
The Initial Commit main that is called when ADF is installed to commit the
initial bootstrap repository content.
"""

import os
import logging
from typing import Mapping, Optional, Union, List, Dict, Any, Tuple
from dataclasses import dataclass, fields
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import re
import boto3
import jinja2
from cfn_custom_resource import (  # pylint: disable=unused-import
    lambda_handler,
    create,
    update,
    delete,
)

# pylint: disable=invalid-name

PhysicalResourceId = str
Data = Mapping[str, str]

HERE = Path(__file__).parent
NOT_YET_CREATED = "NOT_YET_CREATED"
CC_CLIENT = boto3.client("codecommit")
CONFIG_FILE_REGEX = re.compile(r"\A.*[.](yaml|yml|json)\Z", re.I)
REWRITE_PATHS: Dict[str, str] = {
    "bootstrap_repository/adf-bootstrap/example-global-iam.yml": (
        "adf-bootstrap/global-iam.yml"
    ),
    "adf.yml.j2": "adf-accounts/adf.yml",
    "adfconfig.yml.j2": "adfconfig.yml",
}
EXECUTABLE_FILES: List[str] = [
    "adf-build/shared/helpers/package_transform.sh",
    "adf-build/shared/helpers/retrieve_organization_accounts.py",
    "adf-build/shared/helpers/sync_to_s3.py",
    "adf-build/shared/helpers/sts.sh",
    "adf-build/shared/helpers/terraform/adf_terraform.sh",
    "adf-build/shared/helpers/terraform/install_terraform.sh",
]

ADF_LOG_LEVEL = os.environ.get("ADF_LOG_LEVEL", "INFO")
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(ADF_LOG_LEVEL)

PR_DESCRIPTION = """ADF Version {0}

You can find the changelog at:
https://github.com/awslabs/aws-deployment-framework/releases/tag/{0}

This PR was automatically created when you deployed version {0} of the
AWS Deployment Framework.

Review this PR to understand what changes will be made to your bootstrapping
repository. If you also made changes to the repository yourself,
you might have to resolve merge conflicts before you can merge this PR.

Merge this PR to complete the deployment of the version {0} of the
AWS Deployment Framework.
"""


@dataclass
class CustomResourceProperties:
    # pylint: disable=too-many-instance-attributes
    ServiceToken: str
    RepositoryArn: str
    DirectoryName: str
    Version: str
    DefaultBranchName: Optional[str] = None
    CrossAccountAccessRole: Optional[str] = None
    DeploymentAccountRegion: Optional[str] = None
    ExistingAccountId: Optional[str] = None
    DeploymentAccountFullName: Optional[str] = None
    DeploymentAccountEmailAddress: Optional[str] = None
    DeploymentAccountAlias: Optional[str] = None
    TargetRegions: Optional[List[str]] = None
    NotificationEndpoint: Optional[str] = None
    NotificationEndpointType: Optional[str] = None
    ProtectedOUs: Optional[List[str]] = None

    def __post_init__(self):
        if self.NotificationEndpoint:
            self.NotificationEndpointType = (
                "email"
                if self.NotificationEndpoint.find("@") > 0
                else "slack"
            )


def to_dict(datacls_or_dict: Any) -> dict:
    if isinstance(datacls_or_dict, CustomResourceProperties):
        return datacls_or_dict.__dict__
    return datacls_or_dict


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
        # Used to filter out any properties that this class does not know about
        custom_resource_fields = list(map(
            lambda a: a.name,
            fields(CustomResourceProperties),
        ))
        self.ResourceProperties = CustomResourceProperties(
            **{
                key: value for key, value in to_dict(
                    self.ResourceProperties
                ).items()
                if key in custom_resource_fields
            }
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
        super().__post_init__()
        custom_resource_fields = list(map(
            lambda a: a.name,
            fields(CustomResourceProperties),
        ))
        self.OldResourceProperties = CustomResourceProperties(
            **{
                key: value for key, value in to_dict(
                    self.OldResourceProperties
                ).items()
                if key in custom_resource_fields
            }
        )


def chunks(list_to_chunk, number_to_chunk_into):
    """
    Split the list in segments of number_to_chunk_into.

    Args:
        list_to_chunk (list(Any)): The list to split into chunks.
        number_to_chunk_into (int): The number per chunk that is allowed max.

    Returns:
        generator(list(Any)): The list of chunks of the list_to_chunk, where
            each item in the list of chunks contains at most
            number_to_chunk_into elements.
    """
    number_per_chunk = max(1, number_to_chunk_into)
    return (
        list_to_chunk[item:item + number_per_chunk]
        for item in range(0, len(list_to_chunk), number_per_chunk)
    )


def generate_commit_input(
    repo_name,
    version,
    index,
    branch="main",
    parent_commit_id=None,
    puts=None,
    deletes=None,
):
    """
    Generate the input used to create a commit with the CodeCommit client.

    Args:
        repo_name (str): The repository name to crate a commit on.

        version (str): The version of ADF that is installing/updating.

        index (int): The index number of the commit.

        branch (str): The branch to create a commit on, defaults to `main`.

        parent_commit_id (str): The parent commit id which this commit will be
            linked to.

        puts (FileToCommit[]): The list of FileToCommit items that need to be
            committed.

        deletes (FileToDelete[]): The list of FileToDelete items that need to
            be removed in this commit.

    Returns:
        dict(str, Any): The create_commit API call details.
    """
    commit_action = "Delete" if deletes else "Create"
    output = {
        "repositoryName": repo_name,
        "branchName": branch,
        "authorName": "AWS ADF Builders Team",
        "email": "adf-builders@amazon.com",
        "commitMessage": (
            f"Automated Commit - {version} {commit_action} Part {index}"
        ),
        "putFiles": puts if puts else [],
        "deleteFiles": deletes if deletes else []
    }
    if parent_commit_id:
        output["parentCommitId"] = parent_commit_id
    return output


def branch_exists(repo_name, branch_name):
    try:
        CC_CLIENT.get_branch(
            repositoryName=repo_name,
            branchName=branch_name,
        )
        return True
    except CC_CLIENT.exceptions.BranchDoesNotExistException:
        return False


def determine_unique_branch_name(repo_name, branch_name):
    for index in range(0, 10):
        new_branch_name = (
            branch_name
            if index == 0 else
            f"{branch_name}-no-{index}"
        )
        if not branch_exists(repo_name, new_branch_name):
            return new_branch_name
    # Fallback, use the unix timestamp in the branch name
    timestamp = round(datetime.now(timezone.utc).timestamp())
    return f"{branch_name}-at-{timestamp}"


def generate_commits(event, repo_name, directory, parent_commit_id=None):
    """
    Generate the commits for the specified repository.

    Args:
        event (dict(str, Any)): The Create Event or Update Event details.

        repo_name (str): The repository name to create the commits on.

        directory (str): The directory to process.

        parent_commit_id (str): The parent commit to link the commits to.

    Returns:
        str[]: The commit ids of the commits that were created.
    """
    # pylint: disable=too-many-locals
    directory_path = HERE / directory
    version = event.ResourceProperties.Version
    default_branch_name = event.ResourceProperties.DefaultBranchName
    branch_name = version
    if parent_commit_id:
        branch_name = determine_unique_branch_name(
            repo_name=repo_name,
            branch_name=branch_name,
        )
        CC_CLIENT.create_branch(
            repositoryName=repo_name,
            branchName=branch_name,
            commitId=parent_commit_id,
        )
    else:
        branch_name = default_branch_name

    # CodeCommit only allows 100 files per commit, so we chunk them up here
    files_to_commit = get_files_to_commit(directory_path)
    create_first_branch = parent_commit_id is None

    if create_first_branch and directory == "bootstrap_repository":
        adf_config = create_adf_config_file(
            event.ResourceProperties,
            "adfconfig.yml.j2",
            "/tmp/adfconfig.yml",
        )
        initial_sample_global_iam = create_adf_config_file(
            event.ResourceProperties,
            "bootstrap_repository/adf-bootstrap/example-global-iam.yml",
            "/tmp/global-iam.yml",
        )

        create_deployment_account = (
            event.ResourceProperties.DeploymentAccountFullName
            and event.ResourceProperties.DeploymentAccountEmailAddress
        )
        if create_deployment_account:
            adf_deployment_account_yml = create_adf_config_file(
                event.ResourceProperties,
                "adf.yml.j2",
                "/tmp/adf.yml",
            )
            files_to_commit.append(adf_deployment_account_yml)
        files_to_commit.append(adf_config)
        files_to_commit.append(initial_sample_global_iam)

    chunked_files = chunks([f.as_dict() for f in files_to_commit], 99)
    commit_id = parent_commit_id
    commits_created = []
    for index, files in enumerate(chunked_files):
        try:
            commit_id = CC_CLIENT.create_commit(
                **generate_commit_input(
                    repo_name,
                    version,
                    index,
                    branch_name,
                    puts=files,
                    parent_commit_id=commit_id,
                )
            )["commitId"]
            commits_created.append(commit_id)
        except (
            CC_CLIENT.exceptions.FileEntryRequiredException,
            CC_CLIENT.exceptions.NoChangeException
        ):
            pass

    if not create_first_branch:
        # If the branch exists already with files inside, we may need to
        # check which of these files should be deleted:
        files_to_delete = get_files_to_delete(repo_name, directory_path)
        for index, deletes in enumerate(
            chunks([f.as_dict() for f in files_to_delete], 99)
        ):
            try:
                commit_id = CC_CLIENT.create_commit(**generate_commit_input(
                    repo_name,
                    version,
                    index,
                    parent_commit_id=commit_id,
                    branch=branch_name,
                    deletes=deletes
                ))["commitId"]
                commits_created.append(commit_id)
            except (
                CC_CLIENT.exceptions.FileEntryRequiredException,
                CC_CLIENT.exceptions.NoChangeException,
            ):
                pass

    if branch_name != default_branch_name:
        if commits_created:
            CC_CLIENT.create_pull_request(
                title=f'ADF {version} Automated Update PR',
                description=PR_DESCRIPTION.format(version),
                targets=[
                    {
                        'repositoryName': repo_name,
                        'sourceReference': branch_name,
                        'destinationReference': default_branch_name,
                    },
                ],
            )
        else:
            CC_CLIENT.delete_branch(
                repositoryName=repo_name,
                branchName=branch_name,
            )

    return commits_created


def get_commit_id_from_branch(repo_name, branch_name):
    try:
        return CC_CLIENT.get_branch(
            repositoryName=repo_name,
            branchName=branch_name,
        )["branch"]["commitId"]
    except CC_CLIENT.exceptions.BranchDoesNotExistException:
        LOGGER.info(
            "Branch %s on %s does not exist. "
            "Defaulting to creating the branch instead.",
            branch_name,
            repo_name,
        )
        return None


@create()
def create_(
    event: Mapping[str, Any],
    _context: Any,
) -> Tuple[Union[None, PhysicalResourceId], Data]:
    create_event = CreateEvent(**event)
    repo_name = repo_arn_to_name(create_event.ResourceProperties.RepositoryArn)
    default_branch_name = create_event.ResourceProperties.DefaultBranchName
    directory = create_event.ResourceProperties.DirectoryName

    parent_commit_id = get_commit_id_from_branch(
        repo_name,
        default_branch_name,
    )
    commits_created = generate_commits(
        create_event,
        repo_name,
        directory=directory,
        parent_commit_id=parent_commit_id,
    )
    if parent_commit_id is None and commits_created:
        # Return the last commit id that was created.
        return commits_created[-1], {}

    return event.get("PhysicalResourceId"), {}


@update()
def update_(
    event: Mapping[str, Any],
    _context: Any,
) -> Tuple[PhysicalResourceId, Data]:
    update_event = UpdateEvent(**event)
    repo_name = repo_arn_to_name(update_event.ResourceProperties.RepositoryArn)
    default_branch_name = update_event.ResourceProperties.DefaultBranchName

    parent_commit_id = get_commit_id_from_branch(
        repo_name,
        default_branch_name,
    )
    generate_commits(
        update_event,
        repo_name,
        directory=update_event.ResourceProperties.DirectoryName,
        parent_commit_id=parent_commit_id,
    )

    return event["PhysicalResourceId"], {}


@delete()
def delete_(_event, _context):
    pass


def repo_arn_to_name(repo_arn: str) -> str:
    return repo_arn.split(":")[-1]


def get_files_to_delete(
    repo_name: str,
    directory_path: Path,
) -> List[FileToDelete]:
    paginator = CC_CLIENT.get_paginator('get_differences')
    page_iterator = paginator.paginate(
        repositoryName=repo_name,
        afterCommitSpecifier='HEAD',
    )
    unfiltered_file_paths = []
    for page in page_iterator:
        unfiltered_file_paths.extend(list(
            map(
                lambda obj: Path(obj['afterBlob']['path']),
                page['differences'],
            ),
        ))

    file_paths = list(filter(
        # We never want to delete JSON or YAML files
        lambda path: not CONFIG_FILE_REGEX.match(str(path)),
        unfiltered_file_paths,
    ))

    blobs = [
        # Get the paths relative to the directory path so we can compare them
        # correctly.
        str(filename.relative_to(directory_path))
        for filename in directory_path.rglob('*')
    ]

    return [
        FileToDelete(
            str(entry)
        )
        for entry in file_paths
        if str(entry) not in blobs
        and not entry.is_dir()
    ]


def determine_file_mode(entry: Path, directory_path: Path) -> FileMode:
    if str(entry.relative_to(directory_path)) in EXECUTABLE_FILES:
        return FileMode.EXECUTABLE

    return FileMode.NORMAL


def get_files_to_commit(directory_path: Path) -> List[FileToCommit]:
    return [
        FileToCommit(
            str(entry.relative_to(directory_path)),
            determine_file_mode(
                entry,
                directory_path,
            ),
            entry.read_bytes(),
        )
        for entry in directory_path.glob("**/*")
        if not entry.is_dir()
    ]


def create_adf_config_file(
    props: CustomResourceProperties,
    input_file_name: str,
    output_file_name: str,
) -> FileToCommit:
    template = HERE / input_file_name
    adf_config = (
        jinja2.Template(template.read_text(), undefined=jinja2.StrictUndefined)
        .render(vars(props))
        .encode()
    )

    with open(output_file_name, mode="wb") as file:
        file.write(adf_config)

    rewrite_to = REWRITE_PATHS.get(input_file_name)
    if rewrite_to:
        # Overwrite the output file name with the rewritten one
        output_file_name = rewrite_to

    return FileToCommit(output_file_name, FileMode.NORMAL, adf_config)
