# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import time
import os
import boto3
from dotenv import load_dotenv

import service_a_caller
import service_a_unknownapi

load_dotenv()

region = os.environ["api_region"]

boto3_session = boto3.session.Session(region_name=region)
ssm_client = boto3_session.client('ssm')

# color codes to format the output
GREEN = '\033[92m' 
WARNING = '\033[93m' 
OTHER = '\033[95m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
CROSS = '\u2718'
CHECK = '\u2714'

def get_ssm_cmd(instance_id):
    cmd1 = "python3 /tmp/workshop/service_a_caller_sigv4.py"
    response = ssm_client.send_command(InstanceIds=[instance_id],
                                DocumentName='AWS-RunShellScript',
                                Parameters={"commands": [cmd1]}
                                )
    command_id = response.get('Command', {}).get("CommandId", None)
    while True:
        response = ssm_client.list_command_invocations(CommandId=command_id, Details=True)
        if len(response['CommandInvocations']) == 0:
            time.sleep(0.5)
            continue
        invocation = response['CommandInvocations'][0]
        if invocation['Status'] not in ('Pending', 'InProgress', 'Cancelling'):
            break
        time.sleep(0.5)
    command_plugin = invocation['CommandPlugins'][-1]
    output = command_plugin['Output']
    return output

def get_response(caller):
    lambda_client = boto3_session.client('lambda')
    response = lambda_client.invoke(
        FunctionName=caller
    )
    payload = json.loads(response['Payload'].read())
    return payload
        
def parse_result(response):
    response = str(response)
    if "SUCCESS" in response:
        result = ("Allowed","-")
    elif "not authorized" in response:
        if "hit-apigw" in response:
            result = ("Blocked","API Gateway")
        else:
            result = ("Blocked","VPC endpoint")
    elif "Missing Authentication Token" in response:
        result = ("Blocked","API Gateway")
    elif "ConnectTimeout" in response:
        result = ("Blocked","Security Group")
    else:
        result = (response[:100],"unknown")
    
    return result
def print_results(callers):

    # Print result table's header
    titles = ['check', 'result','enforced@']
    #longest_string = max(map(len, checks))
    longest_string = 24
    line = '   '.join(str(x).ljust(longest_string + 4) for x in titles)
    print(BOLD+line+ENDC)
    print('-' * len(line))
    
    for i, caller in enumerate(callers):
        if caller[0] == "service_a_caller":
            check_label ="Expected Caller"
            response = service_a_caller.main()
        elif caller[0] == "service_a_unknownapi":
            check_label ="Expected Caller-Unknown API"
            response = service_a_unknownapi.main()
        elif caller[0][:3] != "arn":
            check_label = f'Unwanted Caller #{i-1}'
            response = get_ssm_cmd(caller[0])
        else:
            check_label = f'Unwanted Caller #{i-1}'
            response = get_response(caller[0])
            
        result = parse_result(response)

        row = [
            check_label,
            result[0],
            result[1]
        ]

        line = '   '.join(str(x).ljust(longest_string + 4) for x in row)
        if row[1] == "Allowed" and caller[1] == "wanted":
            print(GREEN+line+CHECK+ENDC)
        elif row[1] == "Allowed" and caller[1] == "unwanted":
            print(FAIL+line+CROSS+ENDC)
        elif row[1] == "Blocked" and caller[1] == "wanted":
            print(FAIL+line+CROSS+ENDC)
        elif row[1] == "Blocked" and caller[1] == "unwanted":
            print(GREEN+line+CHECK+ENDC)
        elif row[1] == "Blocked?" and caller[1] == "wanted":
            print(WARNING+line+CROSS+ENDC)
        elif row[1] == "Blocked?" and caller[1] == "unwanted":
            print(GREEN+line+CHECK+ENDC)
        
        elif row[1] == "MEH":
            print(WARNING+line+ENDC)
        else:
            print(OTHER+line+ENDC)
def main():
    unwanted_callers_str = ssm_client.get_parameter(Name=os.environ["unwanted_callers_parameter"])['Parameter']['Value']
    unwanted_callers = unwanted_callers_str.split(",")
    
    all_callers = [("service_a_caller","wanted")]
    all_callers.extend([("service_a_unknownapi","unwanted")])
    all_callers.extend([(c,"unwanted") for c in unwanted_callers ])
    print("\n> Started scanning ...\n")
    print_results(all_callers)
    print("\n> Finished scanning.\n")

if __name__ == "__main__":
    main()