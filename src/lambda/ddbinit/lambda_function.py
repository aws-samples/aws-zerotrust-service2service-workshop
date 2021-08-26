# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import cfnresponse

TABLE_NAME = os.environ['TABLE_NAME']

def lambda_handler(event, context):
    if event['RequestType'] != "Create":
        responseData = {}
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)
        return

    dynamodb = boto3.client('dynamodb')

    # putting mock data into DynamoDB
    response = dynamodb.batch_write_item(
        RequestItems={ 
            TABLE_NAME : [ 
                {
                    "PutRequest": { 
                        "Item": {"order_id": {"S":"6472445C25D7"}, "pickup": {"S":"SFO"}, "dropoff": {"S":"SJC"}}
                    }
                },
                { 
                    "PutRequest": { 
                        "Item": { "order_id": {"S":"EDD052166486"},"pickup": {"S":"IAH"},"dropoff": {"S":"IAH"}}
                    }
                },
                { 
                    "PutRequest": { 
                        "Item": {
                            "order_id": {"S":"323E64AF67AB"},"pickup": {"S":"SEA"},"dropoff": {"S":"SFO"} }
                    }
                },                            
            ]
        },
    )
    
    responseData = {}
    cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)

    return