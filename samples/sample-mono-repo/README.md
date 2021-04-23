# Sample Mono Repo showcasing ADF Pipelines

This pipeline will demonstrate how to setup multiple
pipelines that use a mono repo to host the code for two sample applications.

Both applications deploy a simple S3 bucket without granting any permissions.
The point of this sample is to demonstrate how different build and deployment
stages can use the same repository as its source.

Create a new repository that will host the files that are contained inside
this sample folder. In the sample deployment map, the mono repo is named
sample-mono-repo. Whereas the name of the deployment map block refers to the
pipeline name. The later should be unique in order to perform.

In the sample below, we prefixed the name of the mono repo at the start of the
pipeline such that it is easy to determine where the pipeline is defined.

You can extend the deployment map example code depicted below with samples
from the other sample ADF deployments. Although the sample below shows two,
you could use the same technique to create tens of pipelines from the same
repository.

### Deployment Map example

```yaml
  - name: sample-mono-repo-alpha
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
          repository: sample-mono-repo
      build:
        provider: codebuild
        properties:
          image: "STANDARD_4_0"
          spec_filename: apps/alpha/buildspec.yml
      deploy:
        provider: cloudformation
        properties:
          root_dir: apps/alpha
    targets:
      - /banking/testing
      - /banking/production

  - name: sample-mono-repo-beta
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
          repository: sample-mono-repo
      build:
        provider: codebuild
        properties:
          image: "STANDARD_4_0"
          spec_filename: apps/beta/buildspec.yml
      deploy:
        provider: cloudformation
        properties:
          root_dir: apps/beta
    targets:
      - /banking/testing
      - /banking/production
```

## Separate deployment map

Considering that all pipelines will be related to the same repository:
If you are going to define a couple of pipelines, it could be
worthwhile to define these pipelines in a separate deployment map.

This can be achieved by creating a new deployment map file in the
`deployment_maps` folder. If this folder does not exist in the
`aws-deployment-framework-pipelines` repository, you can create one.

The name of the deployment map inside this folder can be anything, as long as
the file extension is `.yml`. For example, you could define a new deployment
map in the file: `deployment_maps/sample-mono-repo.yml`

Make sure that the deployment map file has the same syntax as the
default `deployment_map.yml`. In other words, the array of pipelines should
be stored inside the `pipelines` key.

For example, `deployment_maps/sample-mono-repo.yml` inside the pipelines repo:

```yaml
pipelines:
  - name: sample-mono-repo-alpha
    # The rest of the sample pipeline definition above can be copied here.
```
