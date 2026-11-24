# Sample Python CDK Application (independent CDK version) to showcase ADF Pipelines

This sample deploys a single **"Hello World" AWS Lambda function** using the
**AWS CDK for Python**. Its purpose is to demonstrate two things:

1. **You can manage your CDK version independently from ADF.** This application
   defines its own CDK library version range, and a separately-versioned CDK
   CLI, yet still integrates cleanly with the ADF build tooling. The version
   the application resolves can be newer or older than the one ADF uses. This
   is achieved by building each concern in its own Python virtual environment:

   | Virtual environment | Purpose               | Version                                  |
   | ------------------- | --------------------- | ---------------------------------------- |
   | `py-cdk-venv`       | The CDK application   | `aws-cdk-lib>=2.278.0,<3.0.0`            |
   | `py-adf-venv`       | ADF build tooling     | `aws-cdk-lib~=2.278.0` (provided by ADF) |
   | `py-lambda-venv`    | The Lambda's own deps | `aws-lambda-powertools`, `aws-xray-sdk`  |

   The CDK **CLI** is installed separately again (`aws-cdk@^2`). Because each
   environment is isolated, the CDK library the application resolves never
   conflicts with the library ADF relies on, whichever of the two is newer.

   The CLI floats on the latest 2.x release alongside the library range, as a
   newer `aws-cdk-lib` can require a newer CLI than an older pinned one
   supports (`This CDK CLI is not compatible with the CDK library`). If you
   pin the CLI instead, make sure the library range does not resolve to a
   release newer than the pinned CLI.

2. **A Lambda function managed as source, with its own dependencies.** The
   handler lives in [`src/lambda/sample_fn`](./src/lambda/sample_fn) and declares
   its own [`requirements.txt`](./src/lambda/sample_fn/requirements.txt)
   (AWS Lambda Powertools + X-Ray SDK). Those dependencies are installed and
   zipped inside `py-lambda-venv`, kept separate from the CDK and ADF
   environments.

## How it works

ADF deploys the **synthesized CloudFormation template** through a
CloudFormation action (rather than running `cdk deploy`).
Therefore, the target accounts should not rely on the CDK-bootstrap bucket.
Hence, the template must not reference CDK-staged assets.

This sample therefore delivers the Lambda code through ADF's own parameter
resolvers instead of CDK asset staging:

1. `buildspec.yml` builds `src/lambda/sample_fn` into `lambda-code.zip`.
2. `cdk synth` produces an asset-free `template.yml` whose Lambda code location
   is exposed as two CloudFormation parameters: `AssetBucketParam` and
   `LambdaAssetObjectKeyParam`.
3. During `generate_params.py`, the resolvers in
   [`params/global_us-east-1.yml`](./params/global_us-east-1.yml):
   - `upload:` uploads `lambda-code.zip` to the ADF cross-region asset bucket
     and returns its S3 object key, and
   - `resolve:` reads that bucket's name,

   filling in both template parameters so CloudFormation loads the code with
   `Code.from_bucket` at deploy time.

> **Note:** the region in `params/global_us-east-1.yml` (`us-east-1`) must match
> the region the pipeline deploys to. Add additional `params/global_<region>.yml`
> files for other target regions.

## When ADF and your app need different CDK versions

ADF installs its own CDK library (`aws-cdk-lib~=2.278.0`, defined in
`src/lambda_codebase/initial_commit/bootstrap_repository/adf-build/shared/requirements.txt`)
into `py-adf-venv`. Your application does not have to follow that version.

For example, a new CDK release can ship a security fix that your application
needs right away. With the range in
[`cdk/requirements.txt`](./cdk/requirements.txt) (`>=2.278.0,<3.0.0`), the
next build of your pipeline installs the latest 2.x release into
`py-cdk-venv`, while ADF keeps using its own version in `py-adf-venv`. You get
the fix in your application without waiting for an ADF release that bumps its
CDK version.

The reverse works as well: if a newer CDK release breaks your application,
you can pin an older version in `cdk/requirements.txt` while ADF moves ahead.
The floating CLI remains compatible, as a CDK v2 CLI supports every
`aws-cdk-lib` release that came before it.

## What to look for in the build logs

After the Lambda package is built, the build prints the output of
`pip freeze` for `py-adf-venv` and for `py-cdk-venv`. Compare the two
listings to see that each environment has its own set of packages and
versions. For example, `aws-cdk-lib` can differ between them, as can a
dependency that both environments share, such as `constructs` or `jsii`.
Since each environment resolves its own dependencies, that is expected and
harmless.

## Repository layout

```text
sample-python-cdk-app/
├── buildspec.yml                     # 3 isolated venvs: cdk / adf / lambda
├── cdk/
│   ├── app.py                        # CDK app entrypoint
│   ├── cdk.json
│   ├── requirements.txt              # aws-cdk-lib>=2.278.0,<3.0.0 (own range)
│   └── stack/
│       ├── __init__.py
│       └── sample_stack.py           # single Hello World Lambda
├── params/
│   ├── global.yml
│   └── global_us-east-1.yml          # resolve: asset bucket + upload: zip
└── src/
    └── lambda/
        └── sample_fn/
            ├── app.py                # returns "Hello World"
            └── requirements.txt      # Powertools + X-Ray
```

## Deployment Map example

This pipeline expects _(in the example case)_ an AWS CodeCommit repository on
the account `111111111111` in your main deployment region named
_sample-python-cdk-app_.

```yaml
- name: sample-python-cdk-app
  default_providers:
    source:
      provider: codecommit
      properties:
        account_id: 111111111111
    build:
      provider: codebuild
      properties:
        image: 'STANDARD_7_0'
  targets:
    - /banking/testing
    - /banking/production
```

## Building locally

You can synthesize the template locally to validate the CDK code (this mirrors
what `py-cdk-venv` does in the pipeline):

```bash
cd cdk
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cdk synth
```
