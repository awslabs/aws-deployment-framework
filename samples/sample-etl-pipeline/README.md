## Sample ETL type Pipeline

This pipeline is expecting *(in the example case)* a AWS CodeCommit repository on the account `111111111111` in your main deployment region named *sample-etl-pipeline*.

### Deployment Map example

```yaml
  - name: sample-etl-pipeline
    type: s3-s3
    params:
      - SourceAccountId: 111111111111
      - SourceAccountBucket: banking-etl-bucket-source
      - SourceObjectKey: input.zip
    targets:
      - path: 222222222222
        regions: eu-west-1
        params:
          OutputBucketName: account-blah-bucket-etl
          OutputObjectKey: some_path/output.zip
      - path: 333333333333
        params:
          OutputBucketName: business_unit_bucket-etl
          OutputObjectKey: another/path/output.zip
```


There is no *buildspec.yml* in this sample since we are using S3 as the source and expecting a file *(zip)* as input. Because of this, we have placed the AWS CodeBuild BuildSpec inline in the `s3-s3.yml.j2` file which can have its contents altered to your specific ETL use-case. We will bundle this entire folder up into the `banking-etl-bucket-source` which will contain any ETL types script we might want to run inside AWS CodeBuild. *(Amazon S3 Buckets used as a Source for an AWS CodePipeline must have versioning enabled)*

In order to run this pipeline we are expecting `some_big_file.zip` to land in the S3 Bucket `banking-etl-bucket-source` which is in AWS Account `111111111111`. In normal cases, it is expected that some other mechanism or system is outputting this data into the Bucket as a result of some task completing. In this case with our sample pipeline, we can just zip and upload the content to the required bucket.

```bash
zip -r some_big_file.zip .
aws s3 cp ./some_big_file.zip s3://banking-etl-bucket-source/input.zip
```

**note** AWS CodeBuild offers [different instance types](https://docs.aws.amazon.com/codebuild/latest/userguide/build-env-ref-compute-types.html) that can be used in your pipeline. If you require a different type other than the default *small* instance type you can pass it in as a parameter to your pipeline such as `- ComputeType: BUILD_GENERAL1_LARGE` which is 15GB Memory, 8vCPUs and 128 GB Disk Space.
