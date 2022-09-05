# Integrations Guide
## Introduction
The AWS Deployment Framework enables integrations with external workflows via an Event Bus deployed into the organisational root account.

## Account Management Events
The account management events are emitted at various stages during an execution of the Account Management State Machine.
Currently - events are emitted for the following states:
- ACCOUNT_PROVISIONED
    Emitted when an AWS account is created.
    Contains the account definition from the .yml file as well as the account_id.
- ENTERPRISE_SUPPORT_REQUESTED
    Emitted when the support ticket to AWS Support is raised.
    Contains the account definition from the .yml file as well as the account_id.
- ACCOUNT_ALIAS_CONFIGURED
    Emitted when the accounts alias is configured by ADF.
    The details section contains the account id and the alias value. The resource field also contains the account id
- ACCOUNT_TAGS_CONFIGURED
    Emitted when the accounts tags are updated by ADF.
    The details section contains the account id and the tags. The resource field also contains the account id
- DEFAULT_VPC_DELETED
    Emitted when the default VPC in a region is deleted.
    The details section contains the account id and the region of the VPC. The resource field contains the deleted VPC id.
- ACCOUNT_CREATION_COMPLETE
    Emitted when the state machine completes successfully.
    Contains the account definition from the .yml file as well as the account_id in the resource field.




## Pipeline Management Events
- CROSS_ACCOUNT_RULE_CREATED_OR_UPDATED
    Emitted when a rule is created to trigger pipelines from a different account.
    The details sections contains the source_account_id (The account where the CodeCommit repository is located) and the resource sections contains the deployment account Id (The account where the CodePipeline is located)
- REPOSITORY_CREATED_OR_UPDATED
    Emitted when a codecommit repository is created in a different account than the deployment account.
    The details sections contains the repository_account_id (The account where the CodeCommit repository is located) as well as the stack_name (The CloudFormation stack that creates the repository) and the resource sections contains the repository account Id and the pipeline name


