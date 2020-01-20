#!/usr/bin/env bash
set -e

apt-get install --assume-yes jq
terraform_url=$(curl https://releases.hashicorp.com/index.json | jq '{terraform}' | egrep "linux.*amd64" | sort --version-sort -r | head -1 | awk -F[\"] '{print $4}')
echo "Downloading $terraform_url."
curl -o terraform.zip $terraform_url
unzip terraform.zip
export PATH=$PATH:$(pwd)
terraform --version
