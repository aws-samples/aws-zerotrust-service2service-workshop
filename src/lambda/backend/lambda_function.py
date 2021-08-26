# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.environ['TABLE_NAME']

def backend_logic(orders):
    
    response = orders
    response.insert(0,"SUCCESS")
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain'
        },
        'body': json.dumps(response)
    }

def lambda_handler(event, context):

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)

    try:
        response = table.scan()
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        orders = response['Items']

    return backend_logic(orders)