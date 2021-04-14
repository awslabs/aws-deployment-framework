# Pipeline Types Guide

In order to enhance the flexibility of ADF, it is possible to define custom
pipeline types as separate CDK Stacks (either installed via PIP or added to the
bootstrap repository).

The pipeline type can be (optionally) configured in the parameter section of
the pipeline deployment map.

__Please note__:
Pipeline types is a feature aimed at advanced users and developers of ADF.
Any custom changes made to the adf-bootstrap repository will have to be merged
in when updating ADF versions.


### Adding a new pipeline type

A pipeline can either be added manually into the [cdk_stacks](src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/cdk/cdk_stacks)
folder as a separate python file or installed via [requirements.txt](src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/requirements.txt)
in the adf-build folder.

#### Source Code
This is the file that creates your CDK constructs.
It takes in a single CDK stack that you can interact with and add constructs to.

###### adf-build/shared/cdk/cdk_stacks/custom_pipeline.py

```python
PIPELINE_TYPE = "yourCustomTypeHere"

LOGGER = configure_logger(__name__)


def generate_custom_pipeline(scope: core.Stack, stack_input) -> None: #pylint: disable=R0912, R0915
  # your custom CDK code here
```

This file is where the pipeline type is used to select what CDK stack to
deploy. Import your generate function and pipeline type in and add it to the
file as shown below.

###### adf-build/shared/cdk/cdk_stacks/main.py

```python

from custom_pipeline import generate_custom_pipeline, PIPELINE_TYPE as CUSTOM_PIPELINE
# ...
# removed for brevity.
# ...

def generate_pipeline(self, _pipeline_type, stack_input):
  # ...
  if _pipeline_type == CUSTOM_PIPELINE:
    generate_custom_pipeline(self, stack_input)

```

Add your new pipeline type here.

###### adf-build/shared/schema_validation.py

```python
PARAM_SCHEMA: {
  # ...
  Optional("pipeline_type"): Or("default", "yourCustomTypeHere"),
}

```

To use your new custom pipeline type, add a pipeline_type value to your params
in the deployment map as shown below.

### Using a custom pipeline type

```YAML
pipelines:
  - name: example-pipeline
    default_providers:
      # ...
    params:
      pipeline_type: "yourCustomTypeHere"
      # Other params, like notification_endpoint: <endpoint_value> ...
    targets:
      # ...
```
