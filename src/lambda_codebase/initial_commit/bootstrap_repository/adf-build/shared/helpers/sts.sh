#!/usr/bin/env bash

# Example usage sts 123456789012 adf-terraform-deployment-role
export ROLE=arn:aws:iam::$1:role/$2
temp_role=$(aws sts assume-role --role-arn $ROLE --role-session-name $2-$ADF_PROJECT_NAME)
export AWS_ACCESS_KEY_ID=$(echo $temp_role | jq -r .Credentials.AccessKeyId)
export AWS_SECRET_ACCESS_KEY=$(echo $temp_role | jq -r .Credentials.SecretAccessKey)
export AWS_SESSION_TOKEN=$(echo $temp_role | jq -r .Credentials.SessionToken)
