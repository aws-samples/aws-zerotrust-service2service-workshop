#!/bin/bash
pip3 install aws-requests-auth boto3 python-dotenv
cd /tmp
# NOTE update with latest Event Engine S3 URL
curl -O https://ee-assets-prod-us-east-1.s3.amazonaws.com/modules/1a656bee298f48fcad1bd4938e19b40a/v1/curl-pkg.zip
unzip -qo curl-pkg.zip -d /tmp/workshop/
chmod -R 777 /tmp/workshop/

touch /tmp/workshop/.env

echo python3 /tmp/workshop/scanner.py > /usr/bin/runscanner
chmod 755 /usr/bin/runscanner

echo "* * * * * python3 /tmp/workshop/scanner.py > /dev/null 2>&1" >> /tmp/workshop/cron.txt
echo "* * * * * python3 /tmp/workshop/scanner.py > /dev/null 2>&1" >> /tmp/workshop/cron.txt
echo "* * * * * python3 /tmp/workshop/scanner.py > /dev/null 2>&1" >> /tmp/workshop/cron.txt
echo "* * * * * python3 /tmp/workshop/scanner.py > /dev/null 2>&1" >> /tmp/workshop/cron.txt
crontab /tmp/workshop/cron.txt
