#!/usr/bin/env bash
PATH=$PATH:$(pwd)
export PATH
CURRENT=$(pwd)
terraform --version 
echo "Terraform stage: $TF_STAGE"

tfinit(){
    # retrieve regional S3 bucket name from parameter store
    S3_BUCKET_REGION_NAME=$(aws ssm get-parameter --name /cross_region/s3_regional_bucket/"$AWS_REGION" --region "$AWS_DEFAULT_REGION" | jq .Parameter.Value | sed s/\"//g)
    mkdir -p "$CURRENT"/tmp/"$TF_VAR_TARGET_ACCOUNT_ID"-"$AWS_REGION"
    cd "$CURRENT"/tmp/"$TF_VAR_TARGET_ACCOUNT_ID"-"$AWS_REGION" || exit
    cp -R "$CURRENT"/tf/* "$CURRENT"/tmp/"$TF_VAR_TARGET_ACCOUNT_ID"-"$AWS_REGION"
    # if account related variables exist copy the folder in the work directory
    if [ -d "$CURRENT/tfvars/$TF_VAR_TARGET_ACCOUNT_ID" ]; then
        cp -R "$CURRENT"/tfvars/"$TF_VAR_TARGET_ACCOUNT_ID"/* "$CURRENT"/tmp/"$TF_VAR_TARGET_ACCOUNT_ID"-"$AWS_REGION"
    fi
    cp -R "$CURRENT"/tfvars/global.auto.tfvars "$CURRENT"/tmp/"$TF_VAR_TARGET_ACCOUNT_ID"-"$AWS_REGION"
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
    bash "$CURRENT"/adf-build/helpers/sts.sh "$TF_VAR_TARGET_ACCOUNT_ID" "$TF_VAR_TARGET_ACCOUNT_ROLE"
    terraform plan -out "$ADF_PROJECT_NAME"-"$TF_VAR_TARGET_ACCOUNT_ID"
}
tfapply(){
    terraform apply "$ADF_PROJECT_NAME"-"$TF_VAR_TARGET_ACCOUNT_ID"
}

# if REGIONS is not defined as pipeline parameters use default region
if [[ -z "$REGIONS" ]]
then
    REGIONS=$AWS_DEFAULT_REGION
fi
echo "List of target regions: $REGIONS"
for REGION in $(echo $REGIONS | sed "s/,/ /g")
do  
    AWS_REGION=$REGION
    export TF_VAR_TARGET_REGION=$REGION
    # if TARGET_ACCOUNTS and TARGET_OUS are not defined apply to all accounts
    if [[ -z "$TARGET_ACCOUNTS" ]] && [[ -z "$TARGET_OUS" ]]
    then
        echo "Apply to all accounts" 
        for ACCOUNT_ID in $(jq '.[].AccountId' "$CURRENT"/accounts.json | sed 's/"//g' ) 
        do
            export TF_VAR_TARGET_ACCOUNT_ID=$ACCOUNT_ID
            echo "Running terraform $TF_STAGE on account $ACCOUNT_ID and region $REGION"
            if [[ "$TF_STAGE" = "plan" ]]
            then
                tfinit
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfplan
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
            elif [[ "$TF_STAGE" = "apply" ]]
            then
                tfinit
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfplan
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfapply
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
            else 
                echo "Invalid terraform command"
            fi
        done
    fi

    if ! [[ -z "$TARGET_ACCOUNTS" ]]
    then
        # apply only on a subset of accounts (TARGET_ACCOUNTS)
        echo "List of target account: $TARGET_ACCOUNTS"
        for ACCOUNT_ID in $(echo $TARGET_ACCOUNTS | sed "s/,/ /g")
        do  
            export TF_VAR_TARGET_ACCOUNT_ID=$ACCOUNT_ID
            echo "Running terraform $TF_STAGE on account $ACCOUNT_ID and region $REGION"
            if [[ "$TF_STAGE" = "plan" ]]
            then
                tfinit
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfplan
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
            elif [[ "$TF_STAGE" = "apply" ]]
            then
                tfinit
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfplan
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfapply
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
            else 
                echo "Invalid terraform command"
            fi
        done
    fi

    if ! [[ -z "$TARGET_OUS" ]]
    then
        echo "List target OUs: $TARGET_OUS" 
        for ACCOUNT_ID in $(jq '.[].AccountId' "$CURRENT"/accounts_from_ous.json | sed 's/"//g' ) 
        do
            export TF_VAR_TARGET_ACCOUNT_ID=$ACCOUNT_ID
            echo "Running terraform $TF_STAGE on account $ACCOUNT_ID and region $REGION"
            if [[ "$TF_STAGE" = "plan" ]]
            then
                tfinit
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfplan
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
            elif [[ "$TF_STAGE" = "apply" ]]
            then
                tfinit
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfplan
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
                tfapply
                if [[ $? -ne 0 ]]
                then
                    exit 1
                fi
            else 
                echo "Invalid terraform command"
            fi
        done
    fi
done
