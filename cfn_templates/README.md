## AWS CloudFormation Templates
This folder contains the CloudFormation templates for review purpose only. The CDK app should, ideally, be deployed using `cdk deploy`.

- **ServiceAStack.template.json / ServiceBStack.template.json**

    The CloudFormation templates [synthesized](https://docs.aws.amazon.com/cdk/latest/guide/cli.html#cli-synth) from the CDK stacks in this app at the time of the commit. So, they are static and won't be updated automatically upon making changes into the CDK app. 

- **workshop_parent_stack.yaml**
    
    The parent template for the above two stacks, ServiceA and ServiceB, to simplify and enforce the order of deployment for the two.

:information_source: &nbsp; If you just want to deploy the workshop as is in your environment, and not via CDK, please follow the instructions on the workshop website: https://zerotrust-service2service.workshop.aws/2-environment-build/on-your-own.html