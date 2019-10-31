DEPLOY_ROLE=$1
ROLE=arn:aws:iam::$TARGET_ACCOUNT_ID:role/$DEPLOY_ROLE
temp_role=$(aws sts assume-role --role-arn $ROLE  --role-session-name $TARGET_ACCOUNT_ID-$ADF_PROJECT_NAME)
export AWS_ACCESS_KEY_ID=$(echo $temp_role | jq -r .Credentials.AccessKeyId)
export AWS_SECRET_ACCESS_KEY=$(echo $temp_role | jq -r .Credentials.SecretAccessKey)
export AWS_SESSION_TOKEN=$(echo $temp_role | jq -r .Credentials.SessionToken)
