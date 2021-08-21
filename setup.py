import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="zerotrust_service2service_workshop",
    version="1.0.1",

    description="CDK code for AWS ZeroTrust Service2Service Workshop.",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Faraz Angabini (angabini)",

    package_dir={"": "zerotrust_service2service_workshop"},
    packages=setuptools.find_packages(where="zerotrust_service2service_workshop"),

    install_requires=[
        "pyyaml",
        "aws-cdk.core",
        "aws-cdk.aws-ec2",
        "aws-cdk.aws-s3",
        "aws-cdk.aws-lambda",
        "aws-cdk.aws-logs",
        "aws-cdk.aws-iam",
        "aws-cdk.aws-apigateway",
        "aws_cdk.aws_secretsmanager",
        "aws_cdk.aws_ssm",
        "aws_cdk.aws_dynamodb",
        "aws_cdk.custom_resources",
        "aws_cdk.aws_cloudwatch",
        "aws_cdk.aws_events",
        "aws_cdk.aws_events_targets",
        "aws_cdk.aws_autoscaling",
        "aws_cdk.aws_guardduty",

    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
