#!/usr/bin/env python3

import os
from aws_cdk import App, Environment
from stacks.java_app_stack import JavaAppStack
from stacks.ec2_deployment_stack import EC2DeploymentStack

from dotenv import load_dotenv
load_dotenv()

app = App()

account = os.environ.get('CDK_DEFAULT_ACCOUNT')
region = os.environ.get('CDK_DEFAULT_REGION', 'us-east-1')
environment_name = os.environ.get('ENVIRONMENT_NAME', 'dev')

ec2_deployment_stack = EC2DeploymentStack(
    app,
    f"EC2DeploymentStack-{environment_name}",
    env=Environment(account=account, region=region),
    environment_name=environment_name
)

java_app_stack = JavaAppStack(
    app, 
    f"JavaAppStack-{environment_name}",
    env=Environment(account=account, region=region),
    environment_name=environment_name
)

for stack in [ec2_deployment_stack, java_app_stack]:
    stack.tags.set_tag("Environment", environment_name)
    stack.tags.set_tag("Project", "JavaApp")
    stack.tags.set_tag("ManagedBy", "CDK")

app.synth() 