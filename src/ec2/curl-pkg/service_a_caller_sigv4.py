# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from dotenv import load_dotenv
import os
import boto3
import requests

load_dotenv()
region = os.environ["api_region"]

# Simplifies making Amazon SigV4 calls with the python requests library
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
def call_api(api_id: str, api_key=None): 
    host = api_id+'.execute-api.'+region+'.amazonaws.com'
    base_url = f'https://{host}/api'
    get_url = f'{base_url}/{os.environ["api_resource"]}'

    # Get authentication token - SigV4
    auth = BotoAWSRequestsAuth(aws_host=host, aws_region=region, aws_service='execute-api')
    try:
        response = requests.get(get_url, headers={'x-api-key': api_key}, timeout=2, auth=auth)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return response

def main():
    boto3_session = boto3.session.Session(region_name=region)

    client = boto3_session.client('ssm')
    api_id = client.get_parameter(Name=os.environ["api_id_parameter"])['Parameter']['Value']
    api_secret_arn = client.get_parameter(Name=os.environ["api_secret_parameter"])['Parameter']['Value']

    client = boto3_session.client('secretsmanager')
    api_key = client.get_secret_value(SecretId=api_secret_arn)["SecretString"]

    response = call_api(api_id, api_key)
    return response.text

if __name__ == "__main__":
    print(main())