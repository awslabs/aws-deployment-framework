# Pipelines Repository

## Getting Started

* adf-build/
  * Contains code that gets run by CodeBuild to process the pipeline types and Deployment Map
* pipeline_types/
  * Jinja2 templates for different types of pipelines to use in the Deployment Map
* deployment_map.yml
  * The deployment map

**Important**
This folder should be used as a separate git repository and pushed to the `aws-deployment-framework-pipelines` in the Deployment Account.
You can find the HTTP and SSH url to the repository in the Outputs of the Deployment Accounts bootstrap stack.
The easiest way to do this is to clone the repository from the Deployment Account and move the files in this folder to that git repo, then push the changes.

```bash
CodeCommitHttpURL:
Description: "The CodeCommit HTTP Url"
CodeCommitSshURL:
Description: "The CodeCommit SSH Url"
```

### Clone the `aws-deployment-framework-pipelines`

Setup your credentials to access the `aws-deployment-framework-pipelines` through git. For detailed instructions review the [AWS Documentation](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-https-unixes.html).
Then run the following command to clone the repository to a new folder on your computer.
For the purposes of this documentation we will assume that you place all the folders and files in your home directory, please update the commands to
use the correct folders if you have placed them in another location.

```bash
cd ~
git clone https://git-codecommit.[DEPLOYMENT-ACCOUNT-REGION].amazonaws.com/v1/repos/aws-deployment-framework-pipelines
```

If everything worked you should get a warning about cloning an empty repository that looks like below

```bash
Cloning into 'aws-deployment-framework-pipelines'...
warning: You appear to have cloned an empty repository.
Checking connectivity... done.
```

### Copy the contents from `pipelines_repository` source to the new folder

In your terminal, browse to the folder where this readme is located. It should be similar to `~/aws-deployment-framework/src/pipelines_repository`.
Then move all the contents to the repository you just cloned.

```bash
cd ~/deployment-framework/src/pipelines_repository
cp * ~/aws-deployment-framework-pipelines
```

### Modify the Deployment Map and commit & push changes

Now it's time to modify the deployment map using your favorite text editor. For detailed instructions read the Deployment Map documentation in the [User Guide](/docs/user-guide.md#deployment-map).

*Advanced: You can also modify or add additional pipeline types in the pipeline_types/ folder.*

**Note: Don't make any changes in the build/ folder. It is required to push this as well since it contains the processing logic for the deployment map and pipeline types.**

Now add the files for tracking, commit the changes and push them to the repository in the Deployment Account.

```bash
git add -A
git commit -am "initial commit"
git push origin master
```

The pipelines will now start being provisioned as specified in your organization map. If the specified source (CodeCommit, GitHub etc) doesn't already exist you will need to create those repositories and push your application stacks there to roll them out to the target accounts.