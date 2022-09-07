# Sample CodeBuild VPC usage showcasing ADF Pipelines

This pipeline will demonstrate how-to setup CodeBuild to use a specific VPC.

**Please note**: Before you can deploy CodeBuild in a VPC, you need to follow the
instructions as described in the CodeBuild provider documentation at:
[docs/providers-guide.md](../../docs/providers-guide.md#setup-permissions-for-codebuild-vpc-usage)
This is only required once to allow the CodeBuild service to locate and create
the required resources. Once configured, the permissions allow any pipeline to
make use of VPCs when running CodeBuild steps.

Back to the sample: The pipeline deploys a simple S3 bucket without granting
any permissions. The point of this sample is to demonstrate how different
build and deployment stages can use CodeBuild in a VPC to connect to internal
resources.

Create a new repository that will host the files that are contained inside
this sample folder.

Update the `vpc_id`, `subnet_ids`, and `security_group_ids` attributes to match
your own VPC and subnets that are operational in the deployment account.

### Deployment Map example

```yaml
  - name: sample-codebuild-vpc
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_5_0"
          vpc_id: vpc-01234567890abcdef
          subnet_ids:
            - subnet-1234567890abcdef1
            - subnet-bcdef01234567890a
      deploy:
        provider: cloudformation
    targets:
      - /banking/testing
      - name: integration-tests
        provider: codebuild
        properties:
          image: "STANDARD_5_0"
          spec_filename: testspec.yml
          vpc_id: vpc-01234567890abcdef
          subnet_ids:
            - subnet-1234567890abcdef1
            - subnet-bcdef01234567890a
          security_group_ids:
            - sg-234567890abcdef01
            - sg-cdef01234567890ab
      - /banking/production
```
