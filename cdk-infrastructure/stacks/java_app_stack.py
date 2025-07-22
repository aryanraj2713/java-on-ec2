from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_secretsmanager as secretsmanager,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct


class JavaAppStack(Stack):
    
    def __init__(self, scope: Construct, construct_id: str, environment_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment_name = environment_name
        
        self.vpc = self._create_vpc()
        self.cluster = self._create_ecs_cluster()
        self.ecr_repository = self._create_ecr_repository()
        self.ssh_secret = self._create_ssh_secret()
        self.ecs_service = self._create_ecs_service()
        self._create_outputs()
    
    def _create_vpc(self) -> ec2.Vpc:
        vpc = ec2.Vpc(
            self, 
            "JavaAppVpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ],
            nat_gateways=1
        )
        
        return vpc
    
    def _create_ecs_cluster(self) -> ecs.Cluster:
        cluster = ecs.Cluster(
            self,
            "JavaAppCluster",
            vpc=self.vpc,
            container_insights=True
        )
        
        return cluster
    
    def _create_ecr_repository(self) -> ecr.Repository:
        # Reference existing ECR repository (created by GitHub workflow)
        repository_name = f"java-app-{self.environment_name}"
        
        repository = ecr.Repository.from_repository_name(
            self,
            "JavaAppRepository",
            repository_name
        )
        
        return repository
    
    def _create_ssh_secret(self) -> secretsmanager.Secret:
        secret = secretsmanager.Secret(
            self,
            "SshPrivateKey",
            description="SSH private key for cloning repository",
            secret_name=f"java-app-ssh-key-{self.environment_name}"
        )
        
        return secret
    
    def _create_ecs_service(self) -> ecs_patterns.ApplicationLoadBalancedFargateService:
        
        task_role = iam.Role(
            self,
            "JavaAppTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )
        
        self.ssh_secret.grant_read(task_role)
        
        log_group = logs.LogGroup(
            self,
            "JavaAppLogGroup",
            log_group_name=f"/ecs/java-app-{self.environment_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        task_definition = ecs.FargateTaskDefinition(
            self,
            "JavaAppTaskDefinition",
            memory_limit_mib=2048,
            cpu=1024,
            task_role=task_role
        )
        
        container = task_definition.add_container(
            "JavaAppContainer",
            image=ecs.ContainerImage.from_ecr_repository(self.ecr_repository, "latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="java-app",
                log_group=log_group
            ),
            environment={
                "ENVIRONMENT": self.environment_name,
                "PORT": "9000"
            },
            secrets={
                "SSH_PRIVATE_KEY": ecs.Secret.from_secrets_manager(self.ssh_secret)
            }
        )
        
        container.add_port_mappings(
            ecs.PortMapping(
                container_port=9000,
                protocol=ecs.Protocol.TCP
            )
        )
        
        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "JavaAppService",
            cluster=self.cluster,
            task_definition=task_definition,
            public_load_balancer=True,
            listener_port=80,
            desired_count=2,
            platform_version=ecs.FargatePlatformVersion.LATEST,
            assign_public_ip=False,
            health_check_grace_period=Duration.minutes(5)
        )
        
        service.target_group.configure_health_check(
            path="/health",
            healthy_http_codes="200",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3
        )
        
        scalable_target = service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=10
        )
        
        scalable_target.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.minutes(5),
            scale_out_cooldown=Duration.minutes(2)
        )
        
        scalable_target.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=80,
            scale_in_cooldown=Duration.minutes(5),
            scale_out_cooldown=Duration.minutes(2)
        )
        
        return service
    
    def _create_outputs(self):
        CfnOutput(
            self,
            "LoadBalancerUrl",
            value=f"http://{self.ecs_service.load_balancer.load_balancer_dns_name}",
            description="URL of the Application Load Balancer"
        )
        
        CfnOutput(
            self,
            "EcrRepositoryUri",
            value=self.ecr_repository.repository_uri,
            description="ECR Repository URI"
        )
        
        CfnOutput(
            self,
            "ClusterName",
            value=self.cluster.cluster_name,
            description="ECS Cluster Name"
        )
        
        CfnOutput(
            self,
            "ServiceName",
            value=self.ecs_service.service.service_name,
            description="ECS Service Name"
        ) 