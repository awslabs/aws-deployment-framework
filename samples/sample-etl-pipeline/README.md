## Sample ETL type Pipeline

### Deployment Map example

```yaml
  - name: sample-etl-pipeline
    default_providers:
      source:
        provider: s3
        properties:
          account_id: 111111111111
          bucket_name: banking-etl-bucket-source
          object_key: input.zip
      build:
        enabled: False
      deploy:
        provider: s3
    targets:
      - path: 222222222222
        regions: eu-west-1
        properties:
          bucket_name: account-blah-bucket-etl
          object_key: some_path/output.zip
      - path: 333333333333
        properties:
          bucket_name: business_unit_bucket-etl
          object_key: another/path/output.zip
```
