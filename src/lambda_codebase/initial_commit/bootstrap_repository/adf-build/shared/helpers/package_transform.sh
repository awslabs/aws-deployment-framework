#!/bin/bash
#
# This script will package all source code and send it to an S3 bucket in each region
# where the lambda needs to be deployed to.
#
# ADF_PROJECT_NAME is an environment variable that is passed to the CodeBuild Project
# CODEBUILD_SRC_DIR is an environment variable provided by CodeBuild

set -e

SKIP_BUILD=0

# Walk through the options passed to this script
for i in "$@"
do
  case $i in
    --no-build)
      SKIP_BUILD=1
      ;;
    *)
      echo "Unknown option: $i"
      exit 1
      ;;
  esac
done

if [[ $SKIP_BUILD == 0 ]]; then
  echo "Perform build step"
  # Build our template and its potential dependencies
  sam build
else
  echo "Skip build step"
fi

# Get list of regions supported by this application
echo "Determine which regions need to be prepared"
app_regions=`aws ssm get-parameters --names /deployment/$ADF_PROJECT_NAME/regions --with-decryption --output=text --query='Parameters[0].Value'`
# Convert json list to bash list (space delimited regions)
regions="`echo $app_regions | sed  -e 's/\[\([^]]*\)\]/\1/g' | sed 's/,/ /g' | sed "s/'//g"`"
for region in $regions
do
    if [ $CONTAINS_TRANSFORM ]; then
        echo "Packaging templates for region $region"
        ssm_bucket_name="/cross_region/s3_regional_bucket/$region"
        bucket=`aws ssm get-parameters --names $ssm_bucket_name --with-decryption --output=text --query='Parameters[0].Value'`
        sam package --s3-bucket $bucket --output-template-file $CODEBUILD_SRC_DIR/template_$region.yml --region $region
    else
        # If package is not needed, just copy the file for each region
        echo "Copying template for region $region"
        cp $CODEBUILD_SRC_DIR/template.yml $CODEBUILD_SRC_DIR/template_$region.yml
    fi
done
