#!/usr/bin/env bash

# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

set -xe

# install apache httpd
sudo yum install httpd -y

# install sdk
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"

# install Java
sudo yum install -y java-17-amazon-corretto-headless

# install Maven
yum -y update
sudo yum install -y maven

# sdk version
java -version
mvn --version

# Install Springboot
sdk install springboot

# create a springboot user to run the app as a service
sudo useradd springboot
# springboot login shell disabled
sudo usermod --shell /sbin/nologin springboot

# forward port 80 to 8080
echo "
<VirtualHost *:80>
  ProxyRequests Off
  ProxyPass / http://localhost:8080/
  ProxyPassReverse / http://localhost:8080/
</VirtualHost>
" | sudo tee -a /etc/httpd/conf/httpd.conf > /dev/null

# start the httpd service now and stop it until userdata
sudo systemctl start httpd
sudo systemctl stop httpd

# ensure httpd stays on
sudo systemctl enable httpd
