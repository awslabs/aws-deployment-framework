#!/usr/bin/env bash

# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

set -xe

## Code Deploy Agent Bootstrap Script ##

exec > >(sudo tee /var/log/user-data.log | logger -t user-data -s 2> /dev/console) 2>&1
AUTOUPDATE=false

function installdep() {
  echo "Installing dependencies..."
  if [ ${PLAT} = "ubuntu" ]; then
    apt-get -y update
    # Satisfying even Ubuntu older versions.
    apt-get -y install jq awscli ruby2.0 || apt-get -y install jq awscli ruby
  elif [ ${PLAT} = "amz" ]; then
    yum -y update
    yum install -y aws-cli ruby jq
  fi
  echo "Done installing dependencies."
}

function platformize() {
  # Linux OS detection
  if hash lsb_release; then
    echo "Ubuntu server OS detected"
    export PLAT="ubuntu"
  elif hash yum; then
    echo "Amazon Linux detected"
    export PLAT="amz"
  else
    echo "Unsupported release"
    exit 1
  fi
}

function execute() {
  if [[ "${PLAT}" = "ubuntu" ]] || [[ "${PLAT}" = "amz" ]]; then
    echo "Downloading CodeDeploy Agent..."
    cd /tmp/
    wget https://aws-codedeploy-${REGION}.s3.${REGION}.amazonaws.com/latest/install
    chmod +x ./install

    echo "Installing CodeDeploy Agent..."
    if ./install auto; then
      echo "Installation completed"
      exit 0
    else
      echo "Installation script failed, please investigate"
      rm -f /tmp/install
      exit 1
    fi

  else
    echo "Unsupported platform ''${PLAT}''"
  fi
}

platformize
installdep
export TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
export REGION=$(curl -H "X-aws-ec2-metadata-token: ${TOKEN}" -s http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r ".region")
execute
