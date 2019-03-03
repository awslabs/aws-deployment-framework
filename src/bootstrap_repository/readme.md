## Bootstrap Repository

This repository is where you define your AWS Organizations structure in the form of folders.
In the folders you can define AWS CloudFormation templates that correlate to those specific Organizational Units *(OU)*.

You can define `global.yml` or `regional.yml` templates that will be applied to either the *main* region *(as defined in adfconfig.yml)* in all accounts for a specific OU and if regional is specified, all regions within accounts in that OU.