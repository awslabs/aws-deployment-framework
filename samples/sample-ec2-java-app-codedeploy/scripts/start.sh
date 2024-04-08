#!/usr/bin/env bash

# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

cd /home/ec2-user/server
sudo /usr/bin/java -jar -Dserver.port=80 \
  *.jar > /dev/null 2> /dev/null < /dev/null &
