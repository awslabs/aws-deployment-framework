#!/usr/bin/env bash
set -e

apt-get install --assume-yes jq
TERRAFORM_URL="https://releases.hashicorp.com/terraform/$TERRAFORM_VERSION/terraform_${TERRAFORM_VERSION}_linux_amd64.zip"
echo "Downloading $TERRAFORM_URL."
curl -o terraform.zip $TERRAFORM_URL
unzip terraform.zip
export PATH=$PATH:$(pwd)
terraform --version
