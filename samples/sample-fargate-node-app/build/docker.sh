#!/bin/bash

set -e

$(aws ecr get-login --region $AWS_REGION --no-include-email)
REPOSITORY_URI=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ADF_PROJECT_NAME
IMAGE_TAG=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)

docker build -t $REPOSITORY_URI:latest .
docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$IMAGE_TAG
docker push $REPOSITORY_URI:latest
docker push $REPOSITORY_URI:$IMAGE_TAG

tmp=$(mktemp); jq --arg REPOSITORY_URI "$REPOSITORY_URI" --arg IMAGE_TAG "$IMAGE_TAG"  '.Parameters.Image = $REPOSITORY_URI+":"+$IMAGE_TAG' params/global.json > "$tmp" && mv "$tmp" params/global.json
