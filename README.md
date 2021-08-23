# Zero Trust Workshop - Service2Service Episode - Code


| :zap:       Work In Progress ...   |
|------------------------------------|

<!-- TODO: describe what this creates  -->
This code has two main CDK stacks:
- ServiceA
- ServiceB

<!-- TODO update diagrams -->
High Level Architecture:  
<img src="arch.png" width="600">


# How To Use 

## Requirements
1. python3
2. node
3. aws-cdk


## Need to know, but nothing to do
This project is initialized by `cdk init` and has the standard structure of a Python project.

The initialization process creates a virtualenv within this project, stored under the `.venv`
directory.

## Do
activate the virtualenv:

```bash
source .venv/bin/activate
```

Once the virtualenv is activated, install the required dependencies:

```bash
pip install -r requirements.txt
```

see what stacks are available:

```bash
cdk ls
```

now synthesize the CloudFormation template(s) for this code:

```bash
cdk synth <StackName>
```

### Specific to this app
```bash
# While in the root directory of this repo:
pip3 install aws_requests_auth -t src/lambda/layer/python
```
Why? I create a Lambda layer that contains the `aws_requests_auth` package used by Lambda functions. I avoid pushing the package's files to the repo (.gitignore). So you need to pip install the package after cloning this repo. Then at `cdk deploy` time CDK uses packages installed in `./src/lambda/layer/python` to create the Lambda Layer.

<!-- TODO instruction for lambda from asset vs. bucket -->

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation


 ## Repo structure
<!-- TODO: complete -->
```markdown
.
├── app.py                                  <-- The entry point for this application.
├── config.yml                              <-- [Not a CDK thing] Where the static variables used in this app are defined.
├── README.md                               <-- This instructions file
├── setup.py                                <-- 
├── src                                     <-- Directory for Lambda and EC2 source codes
└── zerotrust_service2service_workshop      <-- Directory for main CDK stacks

```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
