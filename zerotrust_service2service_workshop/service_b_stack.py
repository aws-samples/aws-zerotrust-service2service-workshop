# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import yaml

from aws_cdk import core as cdk

from aws_cdk import (
    aws_lambda as lambda_,
    aws_apigateway as apigw_,
    aws_iam as iam_,
    aws_logs as logs_,
    aws_secretsmanager as secretsmanager_,
    aws_ssm as ssm_,
    aws_dynamodb as ddb_,
    aws_cloudwatch as cw_,
    aws_s3 as s3_,
)

class ServiceBStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str,**kwargs) -> None:
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
        
        orders_table = ddb_.Table(self,"OrdersTable",
            partition_key=ddb_.Attribute(
                name="order_id",
                type=ddb_.AttributeType.STRING
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        # custom resource for populating DDB table with mock data
        ddbinit_lambda = lambda_.Function(self,"DDBInitLambda",
            runtime=lambda_.Runtime.PYTHON_3_8,
            
            code=(lambda_.Code.from_asset("./src/lambda/ddbinit") if configs["dev_mode"] else lambda_.Code.from_bucket(code_bucket,f"{assets_prefix}lambda/ddbinit/lambda-code.zip")),
            
            handler="lambda_function.lambda_handler",
            timeout=cdk.Duration.seconds(configs["lambda_timeout"]),
            environment={
                "TABLE_NAME":orders_table.table_name
            }
        )
        orders_table.grant_write_data(ddbinit_lambda)
        
        # NICE to have: alternative to custom resource, to reduce stack creation time
        ddb_init = cdk.CustomResource(self,"DDBInit",
            service_token=ddbinit_lambda.function_arn,
        )

        backend_lambda = lambda_.Function(self,"BackendLambda",
            runtime=lambda_.Runtime.PYTHON_3_8,

            code=(lambda_.Code.from_asset("./src/lambda/backend") if configs["dev_mode"] else lambda_.Code.from_bucket(code_bucket,f"{assets_prefix}lambda/backend/lambda-code.zip")),

            handler="lambda_function.lambda_handler",
            timeout=cdk.Duration.seconds(configs["lambda_timeout"]),
            environment={
                "TABLE_NAME":orders_table.table_name
            }
        )

        orders_table.grant_read_data(backend_lambda)

        # creating log groups for lambda explicitly so that log groups get deleted after deleing CDK/CFN stack
        for i,lmbd in enumerate([backend_lambda, ddbinit_lambda]):
            logs_.LogGroup(self,f'LogGroup{i}',
                log_group_name=f'/aws/lambda/{lmbd.function_name}',
                removal_policy=cdk.RemovalPolicy.DESTROY
            )

        # API Gateway and its stuff 
        secret = secretsmanager_.Secret(self,"APISecret",
            generate_secret_string=secretsmanager_.SecretStringGenerator(
                exclude_punctuation= True,
            )
        )

        access_log_group = logs_.LogGroup(self,"APIAccessLogs",
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        api = apigw_.LambdaRestApi(self,"ServiceBAPI",
            endpoint_configuration={
                "types":[apigw_.EndpointType.PRIVATE]
            },
            deploy_options={
                "stage_name":"api",
                "access_log_destination":apigw_.LogGroupLogDestination(access_log_group) ,
                "access_log_format": apigw_.AccessLogFormat.clf()
            },
            default_method_options={
                "api_key_required": True
            },
            policy= iam_.PolicyDocument.from_json(configs["api_resource_policy"]),
            handler=backend_lambda,
            proxy=False
        )
        key = api.add_api_key("ApiKey",
            value=secret.secret_value.to_string()
        )
        usage_plan = api.add_usage_plan("UsagePlan",
            api_stages=[{
                "api": api,
                "stage": api.deployment_stage
            }]
        )
        usage_plan.add_api_key(key)
        
        orders = api.root.add_resource("orders")
        get_orders = orders.add_method("GET")

        # For workshop purpose only - this is to determine when calls get blocked at API GW in the scanner.py
        api.add_gateway_response("APICustomResponse",
            type=apigw_.ResponseType.DEFAULT_4_XX,
            templates={
                "application/json": "{ 'message': $context.error.messageString, 'workshopmsg': 'hit-apigw'}"
            }
        )

        unknown_api = apigw_.RestApi(self,"UnknownAPI",
            endpoint_configuration={
                "types":[apigw_.EndpointType.PRIVATE]
            },
            deploy_options={
                "stage_name":"api",
            },
            policy= iam_.PolicyDocument.from_json(configs["api_resource_policy"]),
        )
        unknown_api.root.add_method("PUT",apigw_.MockIntegration(
            integration_responses=[apigw_.IntegrationResponse(
                status_code="200",
                response_templates={"application/json": "{'message':'SUCCESS Mock PUT'}"}
            )],
            request_templates={"application/json": "{'statusCode': 200}"},
            ),
            method_responses=[apigw_.MethodResponse(status_code="200")]
        )
        
        # Storing in Systems Manager Paramete Store - this enables the two template to be deployed in two different accounts.
        ssm_.StringParameter(self,"APIIDParameter",
            parameter_name=f'{configs["params_path"]}service-b-api-id',
            string_value=api.rest_api_id
        )

        ssm_.StringParameter(self,"APISecretNameParameter",
            parameter_name=f'{configs["params_path"]}service-b-api-secret-arn',
            string_value=secret.secret_arn
        )

        ssm_.StringParameter(self,"UnknownAPIIDParameter",
            parameter_name=f'{configs["params_path"]}unknown-api-id',
            string_value=unknown_api.rest_api_id
        )


        # CloudWatch dashboard for API GW
        dashboard = cw_.Dashboard(self,"APICallsDashboard",
            start="-PT2H",
        )

        dashboard.add_widgets(cw_.GraphWidget(
            title="Number of API Calls",
            left=[
                cw_.Metric(
                    metric_name="Count",
                    label="Total API Calls",
                    namespace="AWS/ApiGateway",
                    dimensions={"ApiName": api.rest_api_name},
                    statistic="SampleCount"
                ),
                cw_.Metric(
                    metric_name="4XXError",
                    label="Unauthorized Calls",
                    namespace="AWS/ApiGateway",
                    dimensions={"ApiName": api.rest_api_name},
                    statistic="Sum"
                )
            ],
            left_y_axis=cw_.YAxisProps(
                min= 0
            ),
            width=20,
            period=cdk.Duration.minutes(1),
        ))

        cdk.CfnOutput(self,"APIMethodARN",
                        value=get_orders.method_arn
        )