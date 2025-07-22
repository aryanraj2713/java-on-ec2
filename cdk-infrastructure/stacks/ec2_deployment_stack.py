from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct


class EC2DeploymentStack(Stack):
    
    def __init__(self, scope: Construct, construct_id: str, environment_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment_name = environment_name
        
        self.vpc = self._create_vpc()
        self.security_group = self._create_security_group()
        self.iam_role = self._create_iam_role()
        self.instance_profile = self._create_instance_profile()
        self.key_pair = self._create_key_pair()
        self._create_cloudwatch_logs()
        self._create_outputs()
    
    def _create_vpc(self) -> ec2.Vpc:
        vpc = ec2.Vpc(
            self,
            "DeploymentVpc",
            ip_addresses=ec2.IpAddresses.cidr("10.1.0.0/16"),
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                )
            ],
            nat_gateways=0
        )
        
        return vpc
    
    def _create_security_group(self) -> ec2.SecurityGroup:
        security_group = ec2.SecurityGroup(
            self,
            "DeploymentSecurityGroup",
            vpc=self.vpc,
            description="Security group for EC2 deployment instances",
            allow_all_outbound=True
        )
        
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "SSH access"
        )
        
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(9000),
            "Java application port"
        )
        
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "HTTP access"
        )
        
        return security_group
    
    def _create_iam_role(self) -> iam.Role:
        role = iam.Role(
            self,
            "EC2DeploymentRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy")
            ]
        )
        
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            resources=[
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*"
            ]
        ))
        
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ],
            resources=[
                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/ec2/*"
            ]
        ))
        
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ec2:DescribeInstances",
                "ec2:DescribeTags",
                "ec2:TerminateInstances"
            ],
            resources=["*"],
            conditions={
                "StringEquals": {
                    "ec2:ResourceTag/AutoShutdown": "true"
                }
            }
        ))
        
        role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudformation:SignalResource"
            ],
            resources=["*"]
        ))
        
        return role
    
    def _create_instance_profile(self) -> iam.InstanceProfile:
        instance_profile = iam.InstanceProfile(
            self,
            "EC2DeploymentInstanceProfile",
            role=self.iam_role,
            instance_profile_name=f"EC2-DeploymentRole-{self.environment_name}"
        )
        
        return instance_profile
    
    def _create_key_pair(self) -> ec2.KeyPair:
        key_pair = ec2.KeyPair(
            self,
            "DeploymentKeyPair",
            key_pair_name=f"deployment-keypair-{self.environment_name}",
            type=ec2.KeyPairType.RSA,
            format=ec2.KeyPairFormat.PEM
        )
        
        return key_pair
    
    def _create_cloudwatch_logs(self):
        logs.LogGroup(
            self,
            "DeploymentLogGroup",
            log_group_name="/aws/ec2/deployment",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        logs.LogGroup(
            self,
            "UserDataLogGroup",
            log_group_name="/aws/ec2/userdata",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )
    
    def _create_outputs(self):
        CfnOutput(
            self,
            "SecurityGroupId",
            value=self.security_group.security_group_id,
            description="Security Group ID for EC2 instances"
        )
        
        CfnOutput(
            self,
            "SubnetId",
            value=self.vpc.public_subnets[0].subnet_id,
            description="Public Subnet ID for EC2 instances"
        )
        
        CfnOutput(
            self,
            "KeyPairName",
            value=self.key_pair.key_pair_name,
            description="Key Pair name for EC2 instances"
        )
        
        CfnOutput(
            self,
            "IAMRoleName",
            value=self.iam_role.role_name,
            description="IAM Role name for EC2 instances"
        )
        
        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID for deployment infrastructure"
        ) 