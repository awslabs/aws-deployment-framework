#!/bin/bash

# install apache httpd
sudo yum install httpd -y

# install sdk
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"

# install java 8
sudo yum install java-1.8.0 -y
# remove java 1.7
sudo yum remove java-1.7.0-openjdk -y

# install maven
sudo wget http://repos.fedorapeople.org/repos/dchen/apache-maven/epel-apache-maven.repo -O /etc/yum.repos.d/epel-apache-maven.repo
sudo sed -i s/\$releasever/7/g /etc/yum.repos.d/epel-apache-maven.repo
sudo yum install -y apache-maven

# sdk version
java -version
mvn --version

# Install Springboot
sdk install springboot

# create a springboot user to run the app as a service
sudo useradd springboot
# springboot login shell disabled
sudo chsh -s /sbin/nologin springboot

# forward port 80 to 8080
echo "<VirtualHost *:80>
  ProxyRequests Off
  ProxyPass / http://localhost:8080/
  ProxyPassReverse / http://localhost:8080/
</VirtualHost>" >> sudo /etc/httpd/conf/httpd.conf

# start the httpd service now and stop it until userdata
sudo service httpd start
sudo service httpd stop

# ensure httpd stays on
sudo chkconfig httpd on