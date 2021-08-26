# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import cfnresponse

region = os.environ["region"]

gd_client = boto3.client('guardduty',region_name=region)

def lambda_handler(event, context):

    if event['RequestType'] != "Create":
        responseData = {}
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)
        return
            
    detector=gd_client.list_detectors()

    if len(detector['DetectorIds']) <= 0:
        print('GuardDuty Detector does not exist in Region ' + region)
        print('Creating Detector in ' + region + ' ...')
        gd_client.create_detector(Enable=True)
        detector=gd_client.list_detectors()


    detector_id = detector['DetectorIds'][0]
    print('Detector exists in Region ' + region + ' Detector Id: ' + detector_id)
    for i in range(8):
        print('Creating sample finding ...')
        response = gd_client.create_sample_findings(
            DetectorId=detector_id,
            FindingTypes=['PrivilegeEscalation:IAMUser/AnomalousBehavior']
        )

    responseData = {}
    cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)

    return