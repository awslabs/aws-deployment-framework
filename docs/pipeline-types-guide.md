# Pipeline Types Guide

In order to enhance the flexibility of ADF, it's possible to define custom pipeline types as separate CDK Stacks (either installed via PIP or added to the bootstrap repository)

The pipeline type can be (optionally) configured in the parameter section of the pipeline deployment map

### Adding a new pipeline type

A pipeline can either be added manually into the [cdk_stacks](src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/cdk/cdk_stacks) folder as a seperate python file or installed via [requirements.txt](src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/requirements.txt) in the adf-build folder.

#### Source Code
###### adf-build/shared/cdk/cdk_stacks/custom_pipeline.py
```python
PIPELINE_TYPE = "YourCustomTypeHere"

LOGGER = configure_logger(__name__)


def generate_custom_pipeline(scope: core.Stack, stack_input) -> None: #pylint: disable=R0912, R0915
  # your custom CDK code here

```
###### adf-build/shared/cdk/cdk_stacks/main.py
```python

from custom_pipeline import generate_custom_pipeline, PIPELINE_TYPE as CUSTOM_PIPELINE
...
# removed for brevity.
...

def generate_pipeline(self, _pipeline_type, stack_input):
  ...
  if _pipeline_type == CUSTOM_PIPELINE:
          generate_custom_pipeline(self, stack_input)

```

###### adf-build/shared/schema_validation.py
```python
PARAM_SCHEMA: {
    ...
    ...
    
    Optional("pipeline_type"): Or('Default', "CDK", "YourCustomTypeHere"),
    }

```



### Using a custom pipeline type

```YAML
params:
  notification_endpoint: <endpoint_value>
  ...
  pipeline_type: "YourCustomTypeHere"
  ```
