#!/usr/bin/env bash
PATH=$PATH:$(pwd)
export PATH
CURRENT=$(pwd)
terraform --version
echo "Terraform stage: $TF_STAGE"

tfinit(){
    # retrieve regional S3 bucket name from parameter store
    S3_BUCKET_REGION_NAME=$(aws ssm get-parameter --name "/cross_region/s3_regional_bucket/$AWS_REGION" --region "$AWS_DEFAULT_REGION" | jq .Parameter.Value | sed s/\"//g)
    mkdir -p "${CURRENT}/tmp/${TF_VAR_TARGET_ACCOUNT_ID}-${AWS_REGION}"
    cd "${CURRENT}/tmp/${TF_VAR_TARGET_ACCOUNT_ID}-${AWS_REGION}" || exit
    cp -R "${CURRENT}"/tf/* "${CURRENT}/tmp/${TF_VAR_TARGET_ACCOUNT_ID}-${AWS_REGION}"
    # if account related variables exist copy the folder in the work directory
    if [ -d "${CURRENT}/tfvars/${TF_VAR_TARGET_ACCOUNT_ID}" ]; then
        cp -R "${CURRENT}/tfvars/${TF_VAR_TARGET_ACCOUNT_ID}"/* "${CURRENT}/tmp/${TF_VAR_TARGET_ACCOUNT_ID}-${AWS_REGION}"
    fi
    if [ -f "${CURRENT}/tfvars/global.auto.tfvars" ]; then
        cp -R "${CURRENT}/tfvars/global.auto.tfvars" "${CURRENT}/tmp/${TF_VAR_TARGET_ACCOUNT_ID}-${AWS_REGION}"
    fi
    terraform init \
        -backend-config "bucket=$S3_BUCKET_REGION_NAME" \
        -backend-config "region=$AWS_REGION" \
        -backend-config "key=$ADF_PROJECT_NAME/$ACCOUNT_ID.tfstate" \
        -backend-config "dynamodb_table=adf-tflocktable"

    echo "Bucket: $S3_BUCKET_REGION_NAME"
    echo "Region: $AWS_REGION"
    echo "Key:    $ADF_PROJECT_NAME/$ACCOUNT_ID.tfstate"
    echo "DynamoDB table: adf-tflocktable"
}
tfplan(){
    DATE=$(date +%Y-%m-%d)
    TS=$(date +%Y%m%d%H%M%S)
    bash "${CURRENT}/adf-build/helpers/sts.sh" "${TF_VAR_TARGET_ACCOUNT_ID}" "${TF_VAR_TARGET_ACCOUNT_ROLE}"
    terraform plan -out "${ADF_PROJECT_NAME}-${TF_VAR_TARGET_ACCOUNT_ID}" 2>&1 | tee -a "${ADF_PROJECT_NAME}-${TF_VAR_TARGET_ACCOUNT_ID}-${TS}.log"
    # Save Terraform plan results to the S3 bucket
    aws s3 cp "${ADF_PROJECT_NAME}-${TF_VAR_TARGET_ACCOUNT_ID}-${TS}.log" "s3://${S3_BUCKET_REGION_NAME}/${ADF_PROJECT_NAME}/tf-plan/${DATE}/${TF_VAR_TARGET_ACCOUNT_ID}/${ADF_PROJECT_NAME}-${TF_VAR_TARGET_ACCOUNT_ID}-${TS}.log"
    echo "Path to terraform plan s3://$S3_BUCKET_REGION_NAME/$ADF_PROJECT_NAME/tf-plan/$DATE/$TF_VAR_TARGET_ACCOUNT_ID/$ADF_PROJECT_NAME-$TF_VAR_TARGET_ACCOUNT_ID-$TS.log"
}
tfapply(){
    terraform apply "${ADF_PROJECT_NAME}-${TF_VAR_TARGET_ACCOUNT_ID}"
}
tfplandestroy(){
    terraform plan -destroy -out "${ADF_PROJECT_NAME}-${TF_VAR_TARGET_ACCOUNT_ID}-destroy"
}
tfdestroy(){
    terraform apply "${ADF_PROJECT_NAME}-${TF_VAR_TARGET_ACCOUNT_ID}-destroy"
}
tfrun(){
    export TF_VAR_TARGET_ACCOUNT_ID=$ACCOUNT_ID
    echo "Running terraform $TF_STAGE on account $ACCOUNT_ID and region $REGION"
    if [[ "$TF_STAGE" = "init" ]]
    then
        set -e
        tfinit
        set +e
    elif [[ "$TF_STAGE" = "plan" ]]
    then
        set -e
        tfinit
        tfplan
        set +e
    elif [[ "$TF_STAGE" = "apply" ]]
    then
        set -e
        tfinit
        tfplan
        tfapply
        set +e
    elif [[ "$TF_STAGE" = "destroy" ]]
    then
        set -e
        tfinit
        tfplandestroy
        tfdestroy
        set +e
    else
        echo "Invalid Terraform stage: TF_STAGE = $TF_STAGE"
        exit 1
    fi
}

# if REGIONS is not defined as pipeline parameters use default region
if [[ -z "$REGIONS" ]]
then
    REGIONS=$AWS_DEFAULT_REGION
fi
echo "List of target regions: $REGIONS"
for REGION in $(echo "$REGIONS" | sed "s/,/ /g")
do
    AWS_REGION=$(echo -n "$REGION" | sed 's/^[ \t]*//;s/[ \t]*$//')  # sed trims whitespaces
    export TF_VAR_TARGET_REGION=$AWS_REGION
    # if TARGET_ACCOUNTS and TARGET_OUS are not defined apply to all accounts
    if [[ -z "$TARGET_ACCOUNTS" ]] && [[ -z "$TARGET_OUS" ]]
    then
        echo "Apply to all accounts"
        for ACCOUNT_ID in $(jq '.[].AccountId' "${CURRENT}/accounts.json" | sed 's/"//g' )
        do
            tfrun
        done
    fi

    if ! [[ -z "$TARGET_ACCOUNTS" ]]
    then
        # apply only on a subset of accounts (TARGET_ACCOUNTS)
        echo "List of target account: $TARGET_ACCOUNTS"
        for ACCOUNT_ID in $(echo "$TARGET_ACCOUNTS" | sed "s/,/ /g")
        do
            tfrun
        done
    fi

    if ! [[ -z "$TARGET_OUS" ]]
    then
        echo "List target OUs: $TARGET_OUS"
        for ACCOUNT_ID in $(jq '.[].AccountId' "${CURRENT}/accounts_from_ous.json" | sed 's/"//g' )
        do
            tfrun
        done
    fi
done
