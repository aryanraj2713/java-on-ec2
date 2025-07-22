# Java Application Deployment Solution

This repository contains a comprehensive deployment solution for a Java application using Python, AWS CDK, Docker, and GitHub Actions.

## 🏗️ Architecture Overview

The solution includes:

1. **Python Deployment Script** - Clones repository via SSH and starts Java process
2. **Docker Container** - Containerizes the Java application for cloud deployment
3. **AWS CDK Infrastructure** - Creates ECS cluster with Application Load Balancer
4. **GitHub Actions CI/CD** - Automated build, test, and deployment pipeline

## 📋 Prerequisites

### Local Development
- Python 3.9+
- Java 17+
- Docker
- Git
- AWS CLI configured
- Node.js (for CDK)

### AWS Account
- AWS account with appropriate permissions
- AWS CLI configured with credentials
- CDK bootstrapped in target region

### GitHub Repository
- GitHub repository with Actions enabled
- Required secrets configured (see Setup section)

## 🚀 Quick Start

### 1. Local Development Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd <repo-name>

# Make deployment script executable
chmod +x deployment_script.py

# Test local deployment (requires SSH access to target repo)
python3 deployment_script.py git@github.com:your-org/your-java-repo.git
```

### 2. Docker Setup

```bash
# Build Docker image
docker build -t java-app-deployer .

# Run container (requires SSH key and repo URL)
docker run -e SSH_PRIVATE_KEY="$(cat ~/.ssh/id_rsa)" \
  java-app-deployer \
  python3 /usr/local/bin/deployment_script.py \
  git@github.com:your-org/your-java-repo.git \
  --daemon
```

### 3. AWS Infrastructure Deployment

```bash
# Install CDK dependencies
cd cdk-infrastructure
pip install -r requirements.txt

# Bootstrap CDK (first time only)
export ENVIRONMENT_NAME=dev
cdk bootstrap

# Deploy infrastructure
cdk deploy
```

### 4. GitHub Actions Setup

Add the following secrets to your GitHub repository:

- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key

The workflow will automatically trigger on pushes to `main` or `develop` branches.

## 📁 Project Structure

```
.
├── deployment_script.py          # Python script for local deployment
├── Dockerfile                   # Container definition
├── build.gradle                # Java build configuration
├── src/                        # Java source code
│   └── main/java/com/primechecker/
│       └── PrimeChecker.java   # Java application
├── cdk-infrastructure/         # AWS CDK code
│   ├── app.py                 # CDK app entry point
│   ├── requirements.txt       # Python dependencies
│   └── stacks/
│       └── java_app_stack.py  # Infrastructure definition
└── .github/workflows/
    └── deploy.yml             # CI/CD pipeline
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT_NAME` | Deployment environment | `dev` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `PORT` | Java application port | `9000` |

### CDK Configuration

The CDK stack creates:
- VPC with public/private subnets
- ECS Fargate cluster
- Application Load Balancer
- ECR repository
- Auto-scaling policies
- CloudWatch logs

## 🔒 Security Considerations

### SSH Key Management
- SSH private keys are stored in AWS Secrets Manager
- Container runs as non-root user
- ECR images are scanned for vulnerabilities

### Network Security
- ECS tasks run in private subnets
- Load balancer in public subnets
- Security groups restrict access

### Access Control
- IAM roles with least privilege
- ECS task roles for AWS service access
- Secrets Manager for sensitive data

## 🚦 CI/CD Pipeline

The GitHub Actions workflow includes:

1. **Build & Test** - Compiles Java code and runs tests
2. **Docker Build** - Creates and pushes container image to ECR
3. **Infrastructure** - Deploys/updates AWS infrastructure
4. **Security Scan** - Scans container images for vulnerabilities
5. **Health Check** - Verifies application deployment

### Deployment Environments

- **dev** - Automatic deployment from `develop` branch
- **staging** - Manual deployment via workflow dispatch
- **prod** - Automatic deployment from `main` branch

## 🔍 Monitoring & Troubleshooting

### Health Checks
- Load balancer health checks on `/health` endpoint
- ECS service health monitoring
- CloudWatch logs and metrics

### Common Issues

1. **SSH Key Issues**
   ```bash
   # Update SSH key in Secrets Manager
   aws secretsmanager update-secret \
     --secret-id java-app-ssh-key-dev \
     --secret-string "$(cat ~/.ssh/id_rsa)"
   ```

2. **ECR Permission Issues**
   ```bash
   # Login to ECR
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
   ```

3. **ECS Task Failures**
   ```bash
   # Check ECS logs
   aws logs tail /ecs/java-app-dev --follow
   ```

## 🧪 Testing

### Local Testing
```bash
# Test deployment script
python3 deployment_script.py --help

# Test with sample repository
python3 deployment_script.py git@github.com:example/java-app.git --port 8080
```

### Integration Testing
```bash
# Deploy to dev environment
cd cdk-infrastructure
ENVIRONMENT_NAME=dev cdk deploy

# Test load balancer
curl -I http://<load-balancer-dns>/
```

## 📋 Assumptions & Decisions

### Technical Assumptions
1. **Java Application Structure**: JAR file located at `build/libs/project.jar`
2. **Server Port**: Java application listens on port 9000
3. **Health Endpoint**: Application provides `/health` endpoint for monitoring
4. **Git Access**: SSH key-based authentication for repository access
5. **Build System**: Gradle-based build system with standard structure

### Infrastructure Decisions
1. **Container Platform**: AWS ECS Fargate for serverless containers
2. **Load Balancer**: Application Load Balancer for HTTP/HTTPS traffic
3. **Networking**: VPC with public/private subnet architecture
4. **Auto-scaling**: CPU and memory-based scaling policies
5. **Logging**: CloudWatch logs with 1-week retention

### Security Decisions
1. **Secrets Management**: AWS Secrets Manager for SSH keys
2. **Container Security**: Non-root user, minimal base image
3. **Network Security**: Private subnets for application tasks
4. **Image Scanning**: ECR vulnerability scanning enabled
5. **Access Control**: IAM roles with least privilege principle

### Cost Optimization
1. **NAT Gateway**: Single NAT gateway per VPC
2. **Log Retention**: 1-week retention for development environments
3. **Auto-scaling**: Aggressive scale-in policies to reduce costs
4. **Instance Types**: Fargate for pay-per-use pricing model

### Operational Decisions
1. **Multi-AZ**: Deployment across 2 availability zones
2. **Rolling Updates**: Zero-downtime deployments
3. **Health Checks**: Comprehensive health monitoring
4. **Rollback**: Manual rollback capability via GitHub Actions

## 🚀 Deployment Commands

### Manual Deployment
```bash
# Deploy infrastructure
cd cdk-infrastructure
ENVIRONMENT_NAME=prod cdk deploy

# Build and push image
docker build -t java-app .
docker tag java-app:latest <ecr-uri>:latest
docker push <ecr-uri>:latest

# Update ECS service
aws ecs update-service \
  --cluster JavaAppCluster-prod \
  --service JavaAppService \
  --force-new-deployment
```

### Cleanup
```bash
# Destroy infrastructure
cd cdk-infrastructure
ENVIRONMENT_NAME=dev cdk destroy

# Clean up ECR images
aws ecr batch-delete-image \
  --repository-name java-app-dev \
  --image-ids imageTag=latest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test locally
4. Submit a pull request
5. Ensure CI/CD pipeline passes

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review CloudWatch logs
3. Open a GitHub issue with details
4. Contact the development team

---

**Note**: This solution is designed for demonstration purposes. For production use, additional considerations for security, monitoring, backup, and disaster recovery should be implemented. 