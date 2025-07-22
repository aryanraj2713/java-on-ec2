#!/bin/bash

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-eu-north-1}

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
    echo "✅ EC2 infrastructure deployed successfully!"
    echo ""
    echo "The GitHub workflow will now automatically:"
    echo "  - Deploy CDK infrastructure"
    echo "  - Extract security group, subnet, and key pair values"
    echo "  - Retrieve SSH private key from AWS SSM"
    echo "  - Launch EC2 instance and execute deployment"
    echo ""
    echo "=== REQUIRED GITHUB SECRETS (Only 2 needed!) ==="
    echo ""
    echo "Add these secrets to your GitHub repository:"
    echo "1. AWS_ACCESS_KEY_ID - Your AWS access key"
    echo "2. AWS_SECRET_ACCESS_KEY - Your AWS secret key"
    echo ""
    echo "=== SETUP SECRETS IN AWS SECRETS MANAGER ==="
    echo ""
    echo "1. Create SSH key for repository cloning:"
    echo "   ssh-keygen -t rsa -b 4096 -C 'deployment@yourproject.com' -f ~/.ssh/deployment_key"
    echo "   # Add public key to GitHub repository (Settings > Deploy keys)"
    echo "   aws secretsmanager create-secret --name java-app-ssh-key-$ENVIRONMENT --secret-string \"\$(cat ~/.ssh/deployment_key)\""
    echo ""
    echo "2. Store Logfire token in AWS Secrets Manager:"
    echo "   aws secretsmanager create-secret --name LF_TOKEN --secret-string 'your-logfire-token-here'"
    echo ""
    echo "=== NEXT STEPS ==="
    echo "1. Add the 2 GitHub secrets listed above (AWS credentials)"
    echo "2. Setup SSH key and Logfire token in AWS Secrets Manager"
    echo "3. Push code to main/develop branch or manually trigger workflow"
    echo ""
    echo "🎉 Your deployment is now fully automated!"
    
else
    echo "ERROR: Could not find CDK outputs file"
    exit 1
fi 