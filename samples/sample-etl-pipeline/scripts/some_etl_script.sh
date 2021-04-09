#!/bin/bash

set -e

echo "Doing some ETL tasks... This could also be done with a custom CodeBuild Image..."

cat big_data.txt

echo "You can optionally bundle the buildspec.yml in the source zip and have the commands executed that way.."
echo "Don't forget to enable the build stage to support this"
