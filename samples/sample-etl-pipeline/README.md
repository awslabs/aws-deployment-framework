## Sample ETL type Pipeline

### Deployment Map example

```yaml
  - name: sample-etl-pipeline
    type:
      source:
        name: s3
        account_id: 111111111111
        bucket_name: banking-etl-bucket-source
        object_key: input.zip
      deploy:
        name: s3
    targets:
      - path: 222222222222
        regions: eu-west-1
        type:
          deploy:
            bucket_name: account-blah-bucket-etl
            object_key: some_path/output.zip
      - path: 333333333333
        type:
          deploy:
            bucket_name: business_unit_bucket-etl
            object_key: another/path/output.zip
```
