# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from dotenv import load_dotenv
import os
import boto3
import requests

load_dotenv()
region = os.environ["api_region"]

def call_api(api_id: str): 
    host = api_id+'.execute-api.'+region+'.amazonaws.com'
    base_url = f'https://{host}/api'

    try:
        response = requests.put(base_url, timeout=2)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return response

def main():
    boto3_session = boto3.session.Session(region_name=region)

    client = boto3_session.client('ssm')
    api_id = client.get_parameter(Name=os.environ["unknown_api_id_parameter"])['Parameter']['Value']

    response = call_api(api_id)
    return response.text

if __name__ == "__main__":
    print(main())