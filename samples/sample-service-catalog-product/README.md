## Sample Service Catalog Product

This stack imports values from `sample-vpc` and `sample-iam`.

### Deployment Map example
```yaml
  - name: sample-service-catalog-product
    default_providers:
      source:
        provider: codecommit
        properties:
          account_id: 111111111111
      build:
        provider: codebuild
        properties:
          image: "STANDARD_4_0"
    targets:
      - /banking/testing
      - path: /banking/production
        regions: eu-west-1
        name: production
```

### Parameters
In the Parameter files for this specific pipeline we are uploading any of the Product templates *(productX/template.yml)* contained within this Repository. We can upload the templates to S3 and reference their S3 Object URL by using the following example:

```yaml
Parameters:
    ProductXTemplateURL: 'upload:eu-central-1:path:productX/template.yml'
```

In this example, ADF will search for a file in `productX/template.yml` within this repository. If found, this will be uploaded to an Amazon S3 Bucket within the region defined within the value *(region is optional)*. Once uploaded, this string will be replaced by the uploaded S3 object URL *(using a [path style](https://docs.aws.amazon.com/AmazonS3/latest/dev/VirtualHosting.html) url)* and passed into the template as required. If the repository contains numerous Service Catalog products they will require their own folder and upload parameter within their associated parameter files *(or global.yml)*.

If the region is omitted from the value when using the **upload** functionality your default deployment region will be used:

```yaml
Parameters:
    ProductXTemplateURL: 'upload:path:productX/template.yml'
    ProductYTemplateURL: 'upload:path:productY/another_name.yml'
```

In this example, both files within folder `productX` and `productX` will be uploaded to our default deployment region S3 Bucket and have their parameters updated to contain the S3 URL.
