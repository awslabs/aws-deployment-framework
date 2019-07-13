#!/bin/bash

set -e

# This script will package all source code and send it to an S3 bucket in each region
# where the lambda needs to be deployed to.
#
# ADF_PROJECT_NAME is an environment variable that is passed to the CodeBuild Project
# CODEBUILD_SRC_DIR is an environment variable provided by CodeBuild

pip install --upgrade awscli aws-sam-cli -q

# Build our template and its potential dependancies
sam build

# Get list of regions supported by this application
app_regions=`aws ssm get-parameters --names /deployment/$ADF_PROJECT_NAME/regions --with-decryption --output=text --query='Parameters[0].Value'`
# Convert json list to bash list (space delimited regions)
regions="`echo $app_regions | sed  -e 's/\[\([^]]*\)\]/\1/g' | sed 's/,/ /g' | sed "s/'//g"`"
for region in $regions
do
    # Check if the package command actually needs to be run, only needed if there is a Transform
    if grep -q Transform: "$CODEBUILD_SRC_DIR/template.yml"; then
        ssm_bucket_name="/cross_region/s3_regional_bucket/$region"
        bucket=`aws ssm get-parameters --names $ssm_bucket_name --with-decryption --output=text --query='Parameters[0].Value'`
        sam package --s3-bucket $bucket --output-template-file $CODEBUILD_SRC_DIR/template_$region.yml
    else
        # If package is not needed, just copy the file for each region
        cp $CODEBUILD_SRC_DIR/template.yml $CODEBUILD_SRC_DIR/template_$region.yml
    fi
done
