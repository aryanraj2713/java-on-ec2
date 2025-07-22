#!/bin/bash

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-us-east-1}

echo "Setting up infrastructure for environment: $ENVIRONMENT in region: $AWS_REGION"

cd cdk-infrastructure

echo "Installing CDK dependencies..."
pip install -r requirements.txt

echo "Bootstrapping CDK..."
export ENVIRONMENT_NAME=$ENVIRONMENT
cdk bootstrap

echo "Deploying EC2 deployment infrastructure..."
cdk deploy EC2DeploymentStack-$ENVIRONMENT --require-approval never --outputs-file ec2-outputs.json

if [ -f ec2-outputs.json ]; then
    echo ""
    echo "=== INFRASTRUCTURE SETUP COMPLETE ==="
    echo ""
    echo "Add the following secrets to your GitHub repository:"
    echo ""
    
    SECURITY_GROUP_ID=$(cat ec2-outputs.json | jq -r ".\"EC2DeploymentStack-$ENVIRONMENT\".SecurityGroupId")
    SUBNET_ID=$(cat ec2-outputs.json | jq -r ".\"EC2DeploymentStack-$ENVIRONMENT\".SubnetId")
    KEY_PAIR_NAME=$(cat ec2-outputs.json | jq -r ".\"EC2DeploymentStack-$ENVIRONMENT\".KeyPairName")
    
    echo "EC2_SECURITY_GROUP_ID: $SECURITY_GROUP_ID"
    echo "EC2_SUBNET_ID: $SUBNET_ID"
    echo "EC2_KEY_NAME: $KEY_PAIR_NAME"
    echo ""
    
    echo "=== RETRIEVE PRIVATE KEY ==="
    echo "Run this command to get the private key for GitHub secrets:"
    echo ""
    echo "aws ssm get-parameter --name /ec2/keypair/$KEY_PAIR_NAME --with-decryption --query Parameter.Value --output text"
    echo ""
    echo "Add this private key as EC2_PRIVATE_KEY secret in GitHub"
    echo ""
    
    echo "=== NEXT STEPS ==="
    echo "1. Add the above values as GitHub repository secrets"
    echo "2. Ensure you have LOGFIRE_TOKEN secret configured"
    echo "3. Create SSH key secret in AWS Secrets Manager:"
    echo "   aws secretsmanager create-secret --name java-app-ssh-key-$ENVIRONMENT --secret-string 'your-ssh-private-key'"
    echo "4. Run your GitHub Actions workflow"
    
else
    echo "ERROR: Could not find CDK outputs file"
    exit 1
fi 