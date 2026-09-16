# Sample Python CDK Application (independent CDK version) to showcase ADF Pipelines

This sample deploys a single **"Hello World" AWS Lambda function** using the
**AWS CDK for Python**. Its purpose is to demonstrate two things:

1. **You can manage your CDK version independently from ADF.** This application
   pins an _older_ CDK library than ADF itself uses, and a separately-versioned
   CDK CLI, yet still integrates cleanly with the ADF build tooling. This is
   achieved by building each concern in its own Python virtual environment:

   | Virtual environment | Purpose               | Version                                  |
   | ------------------- | --------------------- | ---------------------------------------- |
   | `py-cdk-venv`       | The CDK application   | `aws-cdk-lib==2.266.0`                   |
   | `py-adf-venv`       | ADF build tooling     | `aws-cdk-lib~=2.268.0` (provided by ADF) |
   | `py-lambda-venv`    | The Lambda's own deps | `aws-lambda-powertools`, `aws-xray-sdk`  |

   The CDK **CLI** is pinned separately again (`aws-cdk@2.1140.0`). Because each
   environment is isolated, the older application library (`2.266.0`) never
   conflicts with the newer library ADF relies on (`2.268.0`).

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

## Repository layout

```text
sample-python-cdk-app/
├── buildspec.yml                     # 3 isolated venvs: cdk / adf / lambda
├── cdk/
│   ├── app.py                        # CDK app entrypoint
│   ├── cdk.json
│   ├── requirements.txt              # aws-cdk-lib==2.266.0 (older than ADF)
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
        image: 'STANDARD_8_0'
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
