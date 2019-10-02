# AWS Expunge VPC

## Overview

This template uses a Custom Lambda backed resource to expunge the default VPC within all regions. 

Upon stack deletion the default VPCs will be recreated


## Steps

1. Commit changes to Master branch to trigger the ADF Pipeline and deploy the resources to configured accounts


### Requirements

- Ensure the 'crhelper' package uses requests from the botocore.vendored library as requests is not yet supported
natively within Lambda

### Parameters
- None


### Deployment Map Example
```yaml
- name: expunge-vpc 
  type: github-cloudformation
  action: replace_on_failure 
  contains_transform: true # Required for templates that contain transforms. (eg SAM Templates) 
  params: 
    - Owner: "owner-name" # Repository owner user 
    - OAuthToken: "/tokens/oauth/github" # Name of SSM Param Store object 
    - WebhookSecret: "/tokens/webhooksecret/github" # Name of SSM Param Store object 
    - NotificationEndpoint: joe.bloggs@domain.com # Slack Channel or Email 
    - RestartExecutionOnUpdate: true 
    - BranchName: master 
  targets: 
    - path: [/test] 
      regions: eu-west-1 
      name: test-deployments 
    - approval 
```