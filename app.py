# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3

import yaml

from aws_cdk import core as cdk

from zerotrust_service2service_workshop.service_a_stack import ServiceAStack
from zerotrust_service2service_workshop.service_b_stack import ServiceBStack

app = cdk.App()

# ServiceB is deployed first, so ServiceA (caller) knows about the ServiceB
service_b_stack = ServiceBStack(app,"ServiceBStack",
    # Uncomment the next line if you want to deploy the stack into a specific Account and Region. 
    # Not used for the workshop, as we synth and use the output CloudFormation for deployment. 
    #env=core.Environment(account='123456789012', region='us-east-1'),
    )

service_a_stack = ServiceAStack(app,"ServiceAStack",
    # Below lines make dependency between stacks; good for single-account deployment.
    # To enable for multi-account deployment, we use Systems Manager paramters here. 
    # Additional work will be required to let one account read parameters from other account, 
    # as well grant Lambda and EC2 roles to GetSecretValue from Secrets Manager.
    #api_endpoint=service_b_stack.api_endpoint,
    #api_secret=service_b_stack.api_secret,
    
    # Uncomment the next line if you want to deploy the stack into a specific Account and Region. 
    # Not used for the workshop, as we synth and use the output CloudFormation for deployment. 
    #env=core.Environment(account='123456789012', region='us-east-1'),
    )

# NOTE comment this for final synth, uncomment while developing
service_a_stack.add_dependency(service_b_stack)

with open("./config.yml","r") as f:
    configs = yaml.safe_load(f)

# Tagging the resources deployed by this app.
cdk.Tags.of(app).add("Project", "ZeroTrustWorkshop")
cdk.Tags.of(service_a_stack).add("Owner", "AccountA")
cdk.Tags.of(service_a_stack).add("Service", "ServiceA")
cdk.Tags.of(service_b_stack).add("Owner", "AccountB")
cdk.Tags.of(service_b_stack).add("Service", "ServiceB")

app.synth()