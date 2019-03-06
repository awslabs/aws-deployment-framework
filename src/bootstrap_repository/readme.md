# Bootstrap Templates repository

## Getting Started

* adf-build/
  * Contains code that gets run by CodeBuild to process the pipeline types and Deployment Map
* deployment/
  * Required folder to bootstrap the ADF Deployment account
* adfconfig.yml
  * Configuration file for the template containing bootstrap regions, notification endpoints etc.
* global.yml
  * Default bootstrap template. Will be used if no OU specific global.yml is found for each account.

**Important**
This folder should be used as a separate git repository and pushed to the `aws-deployment-framework-bootstrap` repository in the Organization Master Account in `us-east-1`.
You can find the HTTP and SSH url to the repository in the Outputs of the Organization Master Accounts bootstrap stack.
The easiest way to do this is to clone the repository from the Organization Master Account and move the files in this folder to that git repo, then push the changes.

```bash
CodeCommitHttpURL:
Description: "The CodeCommit HTTP Url"
CodeCommitSshURL:
Description: "The CodeCommit SSH Url"
```

### Clone the `aws-deployment-framework-bootstrap` repository

Setup your credentials to access the pipelines-repository through git. For detailed instructions review the [AWS Documentation](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-https-unixes.html).
Then run the following command to clone the repository to a new folder on your computer.
For the purposes of this documentation we will assume that you place all the folders and files in your home directory, please update the commands to
use the correct folders if you have placed them in another location.

```bash
cd ~
git clone https://git-codecommit.us-east-1.amazonaws.com/v1/repos/aws-deployment-framework-bootstrap
```

If everything worked you should get a warning about cloning an empty repository that looks like below

```bash
Cloning into 'aws-deployment-framework-bootstrap'...
warning: You appear to have cloned an empty repository.
Checking connectivity... done.
```

### Copy the contents from pipelines-repository source to the new folder

In your terminal, browse to the folder where this readme is located. It should be similar to ~/aws-deployment-framework/src/bootstrap_repository.
Then move all the contents to the repository you just cloned.

```bash
cd ~/aws-deployment-framework/src/bootstrap_repository
cp * ~/aws-deployment-framework-bootstrap
```

### Modify the folder structure and commit & push changes

Now it's time to modify the folder structure using your favorite text editor. For detailed instructions read the Bootstrap Templates documentation in the [Admin Guide](/docs/admin-guide.md#bootstrapping-accounts).

**Note: Don't make any changes in the adf-build folder. It is required to push this as well since it contains the processing logic for the deployment map and pipeline types.**

Now add the files for tracking, commit the changes and push them to the repository in the Organization Master Account.

```bash
git add -A
git commit -am "initial commit"
git push origin master
```

The bootstrap templates will now be updated and pushed out to all accounts where there are changes.