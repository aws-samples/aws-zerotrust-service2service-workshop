# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import yaml
from aws_cdk import core as cdk

from aws_cdk import (
    aws_lambda as lambda_,
    aws_ec2 as ec2_,
    aws_iam as iam_,
    aws_secretsmanager as secretsmanager_,
    aws_ssm as ssm_,
    aws_events as events_,
    aws_events_targets as targets_,
    aws_s3 as s3_,
    aws_logs as logs_,
)

with open("./src/ec2/user_data.sh") as f:
    ec2_user_data = f.read()

class ServiceAStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        with open("./config.yml","r") as f:
            configs = yaml.safe_load(f)

        if configs["dev_mode"]:
            pass
        else:
            # AWS Event Engine stuff - the value for these parameters will be available at an event runtime
            assets_bucket = cdk.CfnParameter(self,"EEAssetsBucket",type="String", description="Region-specific assets S3 bucket name.").value_as_string
            assets_prefix = cdk.CfnParameter(self,"EEAssetsKeyPrefix",type="String", description="S3 key prefix where this modules assets are stored. (e.g. modules/my_module/v1/)").value_as_string
         
            code_bucket = s3_.Bucket.from_bucket_name(self,"CodeBucket",
                bucket_name=assets_bucket
            )
        
        # IAM Resources - potentially move to a separate file
        main_instance_role = iam_.Role(self,"ServiceAInstanceRole",
            assumed_by=iam_.ServicePrincipal("ec2.amazonaws.com"),
            description="Allows EC2 instances to call AWS services on your behalf.",
            managed_policies=[
                iam_.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                # In prod, this should be limited to the intended API resource only
                iam_.ManagedPolicy.from_aws_managed_policy_name("AmazonAPIGatewayInvokeFullAccess")
            ]
        )

        lambda_role = iam_.Role(self,"ServiceALambdaRole",
            assumed_by=iam_.ServicePrincipal("lambda.amazonaws.com"),
            description="Allows Lambda functions to call AWS services on your behalf.",
            managed_policies=[
                iam_.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
            ]
        )

        # Getting API secret's ARN, by its name, from parameter store.
        service_b_secret_arn = ssm_.StringParameter.value_for_string_parameter(self,
            f'{configs["params_path"]}service-b-api-secret-arn'
        )

        # Importing the secret so can use high-level grant function of CDK.
        # Alternative would be adding specific permissions to the roles via IAM construct - better for multi-account.
        service_b_secret = secretsmanager_.Secret.from_secret_complete_arn(self,"APISecret",
            secret_complete_arn=service_b_secret_arn
        )
        
        service_b_secret.grant_read(main_instance_role)
        service_b_secret.grant_read(lambda_role)

        lambda_role.add_to_policy(iam_.PolicyStatement(
            effect=iam_.Effect.ALLOW,
            actions=["ssm:GetParameter*"],
            resources=[
                cdk.Arn.format(cdk.ArnComponents(resource='parameter',service='ssm'),self)
                +configs["params_path"]+"*"
            ]
        ))
        
        # Network Resources - potentially move to a separate file
        main_vpc = ec2_.Vpc(self,"ServiceAVPC",
            max_azs=2,
            cidr=configs["main_vpc_cidr"],
            subnet_configuration=[
                ec2_.SubnetConfiguration(
                    subnet_type=ec2_.SubnetType.PRIVATE,
                    name="Private",
                    cidr_mask=24
                ),
                # to allow instances dowload pip and workshop files (IGW,NATGW)
                ec2_.SubnetConfiguration(
                    subnet_type=ec2_.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24
                )
            ],
            # set to 1 only for workshop purpose. Delete the line to get one per AZ.
            nat_gateways=1                    
        )
        
        vpc2 = ec2_.Vpc(self,"OtherVPC",
            max_azs=1,
            cidr=configs["other_vpc_cidr"],
            subnet_configuration=[
                ec2_.SubnetConfiguration(
                    subnet_type=ec2_.SubnetType.PRIVATE,
                    name="Private",
                    cidr_mask=26
                ),
                ec2_.SubnetConfiguration(
                    subnet_type=ec2_.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=26
                )
            ],
            nat_gateways=1                    
        )

        custom_default_secgroup = ec2_.SecurityGroup(self,"MainVPCSecurityGroup",
            security_group_name="MainVPCSecurityGroup",
            vpc=main_vpc
        )
        
        main_instance_secgroup = ec2_.SecurityGroup(self,"ServiceASecurityGroup",
            security_group_name="ServiceASecurityGroup",
            vpc=main_vpc,
        )

        vpce_apigw_secgroup = ec2_.SecurityGroup(self,"APIGWVPCEndpointSecurityGroup",
            security_group_name="APIGWVPCEndpointSecurityGroup",
            vpc=main_vpc,
        )

        cdk.Tags.of(vpce_apigw_secgroup).add("Name","APIGWVPCEndpointSecurityGroup")

        vpc_endpoint_apigw = main_vpc.add_interface_endpoint("APIGWVPCEndpoint", 
            service=ec2_.InterfaceVpcEndpointAwsService.APIGATEWAY,
            security_groups=[vpce_apigw_secgroup]
        )

        vpc_endpoint_ssm = main_vpc.add_interface_endpoint("SSMVPCEndpoint", 
            service=ec2_.InterfaceVpcEndpointAwsService.SSM
        )

        vpc_endpoint_ssmmsg = main_vpc.add_interface_endpoint("SSMMSGVPCEndpoint", 
            service=ec2_.InterfaceVpcEndpointAwsService.SSM_MESSAGES
        )

        vpc2_endpoint_apigw = vpc2.add_interface_endpoint("APIGWVPC2Endpoint", 
            service=ec2_.InterfaceVpcEndpointAwsService.APIGATEWAY
        )

        vpc2_endpoint_ssm = vpc2.add_interface_endpoint("SSMVPC2Endpoint", 
            service=ec2_.InterfaceVpcEndpointAwsService.SSM
        )

        vpc2_endpoint_ssmmsg = vpc2.add_interface_endpoint("SSMMSGVPC2Endpoint", 
            service=ec2_.InterfaceVpcEndpointAwsService.SSM_MESSAGES
        )
        
        # this is a workaround to remove the unintended auto-added tag (VPC name) to vpc endpoint children (security groups)
        for vpce in [vpc_endpoint_apigw, vpc_endpoint_ssm, vpc_endpoint_ssmmsg, vpc2_endpoint_apigw, vpc2_endpoint_ssm, vpc2_endpoint_ssmmsg]:
            cdk.Tags.of(vpce).remove("Name")

        # Compute Resources - potentially move to a separate file
        lambda_layer = lambda_.LayerVersion(self,"WorkshopLayer",

            code=(lambda_.Code.from_asset("./src/lambda/layer") if configs["dev_mode"] else lambda_.Code.from_bucket(code_bucket,f"{assets_prefix}lambda/layer/lambda-code.zip")),

            compatible_runtimes=[lambda_.Runtime.PYTHON_3_8],
            description="The layer containing external packages used in this workshop.",
        )

        caller1_lambda = lambda_.Function(self,"CallerOne",
            runtime=lambda_.Runtime.PYTHON_3_8,

            code=(lambda_.Code.from_asset("./src/lambda/caller_nosigv4") if configs["dev_mode"] else lambda_.Code.from_bucket(code_bucket,f"{assets_prefix}lambda/caller_nosigv4/lambda-code.zip")),

            handler="lambda_function.lambda_handler",
            layers=[lambda_layer],
            timeout=cdk.Duration.seconds(configs["lambda_timeout"]),
            vpc=main_vpc,
            vpc_subnets=ec2_.SubnetSelection(subnets=[main_vpc.private_subnets[1]]),
            security_groups=[custom_default_secgroup],
            role=lambda_role,
            environment= {
                "api_resource":configs["api_resource"],
                "api_region": cdk.Stack.of(self).region,
                "api_id_parameter":f'{configs["params_path"]}service-b-api-id',
                "api_secret_parameter":f'{configs["params_path"]}service-b-api-secret-arn'
            }
        )

        caller2_lambda = lambda_.Function(self,"CallerTwo",
            runtime=lambda_.Runtime.PYTHON_3_8,

            code=(lambda_.Code.from_asset("./src/lambda/caller_nosigv4") if configs["dev_mode"] else lambda_.Code.from_bucket(code_bucket,f"{assets_prefix}lambda/caller_nosigv4/lambda-code.zip")),

            handler="lambda_function.lambda_handler",
            layers=[lambda_layer],
            timeout=cdk.Duration.seconds(configs["lambda_timeout"]),
            vpc=main_vpc,
            vpc_subnets=ec2_.SubnetSelection(subnets=[main_vpc.private_subnets[0]]),
            security_groups=[custom_default_secgroup],
            role=lambda_role,
            environment= {
                "api_resource":configs["api_resource"],
                "api_region": cdk.Stack.of(self).region,
                "api_id_parameter":f'{configs["params_path"]}service-b-api-id',
                "api_secret_parameter":f'{configs["params_path"]}service-b-api-secret-arn'
            },
        )

        caller3_lambda = lambda_.Function(self,"CallerThree",
            runtime=lambda_.Runtime.PYTHON_3_8,
            
            code=(lambda_.Code.from_asset("./src/lambda/caller_sigv4") if configs["dev_mode"] else lambda_.Code.from_bucket(code_bucket,f"{assets_prefix}lambda/caller_sigv4/lambda-code.zip")),

            handler="lambda_function.lambda_handler",
            layers=[lambda_layer],
            timeout=cdk.Duration.seconds(configs["lambda_timeout"]),
            vpc=main_vpc,
            vpc_subnets=ec2_.SubnetSelection(subnets=[main_vpc.private_subnets[0]]),
            security_groups=[custom_default_secgroup],
            role=lambda_role,
            environment= {
                "api_resource":configs["api_resource"],
                "api_region": cdk.Stack.of(self).region,
                "api_id_parameter":f'{configs["params_path"]}service-b-api-id',
                "api_secret_parameter":f'{configs["params_path"]}service-b-api-secret-arn'
            }
        )

        gd_lambda = lambda_.Function(self,"GuardDutyHelper",
            runtime=lambda_.Runtime.PYTHON_3_8,

            code=(lambda_.Code.from_asset("./src/lambda/guardduty_helper") if configs["dev_mode"] else lambda_.Code.from_bucket(code_bucket,f"{assets_prefix}lambda/guardduty_helper/lambda-code.zip")),

            timeout=cdk.Duration.seconds(configs["lambda_timeout"]),
            handler="lambda_function.lambda_handler",
            environment= {
                "region": cdk.Stack.of(self).region
            },
        )
        gd_lambda.role.add_to_policy(iam_.PolicyStatement(
            resources=["*"],
            actions=["guardduty:CreateDetector","guardduty:CreateSampleFindings","guardduty:ListDetectors"]
        ))
        gd_lambda.role.add_to_policy(iam_.PolicyStatement(
            actions=["iam:CreateServiceLinkedRole"],
            resources=["arn:aws:iam::*:role/aws-service-role/guardduty.amazonaws.com/AWSServiceRoleForAmazonGuardDuty*"],
            conditions={"StringLike": {"iam:AWSServiceName": "guardduty.amazonaws.com"}}

        ))

        # NICE to have: alternative to custom resource, to reduce stack creation time
        gd_init = cdk.CustomResource(self,"GDInit",
            service_token=gd_lambda.function_arn
        )

        # creating log groups for lambda explicitly so that log groups get deleted after deleing CDK/CFN stack
        for i,lmbd in enumerate([caller1_lambda, caller2_lambda, caller3_lambda, gd_lambda]):
            logs_.LogGroup(self,f'LogGroup{i}',
                log_group_name=f'/aws/lambda/{lmbd.function_name}',
                removal_policy=cdk.RemovalPolicy.DESTROY
            )

        # Scheduling Lambdas
        one_minute_rule = events_.Rule(self,"ScheduleRuleOne",
            description="Scheduler running every minute",
            schedule=events_.Schedule.rate(cdk.Duration.minutes(1)),
            targets=[
                targets_.LambdaFunction(caller1_lambda),
                targets_.LambdaFunction(caller2_lambda),
                targets_.LambdaFunction(caller3_lambda),
            ]
        )

        # EC2 stuff
        amzn_linux_ami = ec2_.MachineImage.latest_amazon_linux(
            generation=ec2_.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2_.AmazonLinuxEdition.STANDARD,
            virtualization=ec2_.AmazonLinuxVirt.HVM,
            storage=ec2_.AmazonLinuxStorage.GENERAL_PURPOSE
        )

        # to use autoscaling group, uncomment the line below and comment the one after
        #main_instance = autoscaling_.AutoScalingGroup(self,"ServiceA",
        main_instance = ec2_.Instance(self,"ServiceAInstance",
            instance_type=ec2_.InstanceType(configs["instance_type"]),
            machine_image=amzn_linux_ami,
            vpc=main_vpc,
            vpc_subnets=ec2_.SubnetSelection(subnets=[main_vpc.private_subnets[0]]),
            security_group=main_instance_secgroup,
            role=main_instance_role,
            user_data=ec2_.UserData.custom(ec2_user_data)
        )
        main_instance.add_user_data(f'echo api_resource={configs["api_resource"]} >> /tmp/workshop/.env')
        main_instance.add_user_data(f'echo api_region={cdk.Stack.of(self).region} >> /tmp/workshop/.env')
        main_instance.add_user_data(f'echo api_id_parameter={configs["params_path"]}service-b-api-id >> /tmp/workshop/.env')
        main_instance.add_user_data(f'echo api_secret_parameter={configs["params_path"]}service-b-api-secret-arn >> /tmp/workshop/.env')
        main_instance.add_user_data(f'echo unwanted_callers_parameter={configs["params_path"]}service-a-unwanted-callers-list >> /tmp/workshop/.env')
        main_instance.add_user_data(f'echo unknown_api_id_parameter={configs["params_path"]}unknown-api-id >> /tmp/workshop/.env')
        
        other_instance = ec2_.Instance(self,"OtherInstance",
            instance_type=ec2_.InstanceType(configs["instance_type"]),
            machine_image=amzn_linux_ami,
            vpc=vpc2,
            vpc_subnets=ec2_.SubnetSelection(subnets=[vpc2.private_subnets[0]]),
            role=main_instance_role,
            user_data=ec2_.UserData.custom(ec2_user_data)
        )
        other_instance.add_user_data(f'echo api_resource={configs["api_resource"]} >> /tmp/workshop/.env')
        other_instance.add_user_data(f'echo api_region={cdk.Stack.of(self).region} >> /tmp/workshop/.env')
        other_instance.add_user_data(f'echo api_id_parameter={configs["params_path"]}service-b-api-id >> /tmp/workshop/.env')
        other_instance.add_user_data(f'echo api_secret_parameter={configs["params_path"]}service-b-api-secret-arn >> /tmp/workshop/.env')

        # This is for workshop purpose only - to enable scanner to invoke Lambdas and unwanted instance
        caller1_lambda.grant_invoke(main_instance_role)
        caller2_lambda.grant_invoke(main_instance_role)
        caller3_lambda.grant_invoke(main_instance_role)
        main_instance_role.add_to_policy(iam_.PolicyStatement(
            resources=["*"],
            actions=["ssm:SendCommand","ssm:ListCommandInvocations"]
        ))

        # Storing in Systems Manager Paramete Store
        ssm_.StringListParameter(self,"UnwantedCallersListParameter",
            parameter_name=f'{configs["params_path"]}service-a-unwanted-callers-list',
            string_list_value=[
                caller1_lambda.function_arn,
                caller2_lambda.function_arn,
                caller3_lambda.function_arn,
                other_instance.instance_id,
            ]
        )
        
        cdk.CfnOutput(self,"InstanceSession",
            value=f'https://console.aws.amazon.com/systems-manager/session-manager/{main_instance.instance_id}?region={cdk.Stack.of(self).region}'
        )
        
        cdk.CfnOutput(self,"InstanceRoleArn",
            value=main_instance_role.role_arn
        )

        cdk.CfnOutput(self,"ServiceAAccountID",
            value=cdk.Stack.of(self).account
        )

        cdk.CfnOutput(self,"VPCEndpointID",
            value=vpc_endpoint_apigw.vpc_endpoint_id
        )