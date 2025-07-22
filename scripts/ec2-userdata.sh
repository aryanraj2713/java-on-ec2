#!/bin/bash

exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting EC2 user data script at $(date)"

yum update -y

echo "Installing required packages..."
yum install -y git curl wget

echo "Installing Python 3.9 from Amazon Linux Extras..."
amazon-linux-extras install python3.8 -y

echo "Installing Java 17 JDK..."
yum install -y java-17-amazon-corretto-devel

echo "Setting up Python 3.8 as default..."
alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.8 1

echo "Installing Gradle..."
wget https://services.gradle.org/distributions/gradle-8.4-bin.zip -P /tmp
unzip -d /opt /tmp/gradle-8.4-bin.zip
ln -s /opt/gradle-8.4/bin/gradle /usr/local/bin/gradle
chmod +x /usr/local/bin/gradle

echo "Setting up deployment directory..."
mkdir -p /home/ec2-user/deployment
chown ec2-user:ec2-user /home/ec2-user/deployment

echo "Cloning deployment repository..."
cd /home/ec2-user/deployment
git clone https://github.com/$GITHUB_REPOSITORY.git repo || echo "Repository clone failed, will retry with SSH"

if [ -d "repo" ]; then
    cp -r repo/* .
    rm -rf repo
else
    echo "Repository not cloned via HTTPS, SSH will be used later"
fi

echo "Setting up Python environment..."
pip3 install --upgrade pip
pip3 install boto3 logfire botocore

echo "Setting up SSH for git operations..."
mkdir -p /home/ec2-user/.ssh
chown ec2-user:ec2-user /home/ec2-user/.ssh
chmod 700 /home/ec2-user/.ssh

echo "Creating deployment log file..."
touch /var/log/deployment.log
chmod 666 /var/log/deployment.log

echo "Setting up auto-shutdown safety mechanism..."
cat > /opt/auto-shutdown.sh << 'EOL'
#!/bin/bash
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
UPTIME_MINUTES=$(awk '{print int($1/60)}' /proc/uptime)

if [ $UPTIME_MINUTES -gt 60 ]; then
    echo "Instance has been running for over 60 minutes, initiating shutdown..."
    /opt/aws/bin/cfn-signal -e 0 --stack AutoShutdown --resource EC2Instance --region $(curl -s http://169.254.169.254/latest/meta-data/placement/region) || true
    shutdown -h +5 "Auto-shutdown after 60 minutes uptime"
fi
EOL

chmod +x /opt/auto-shutdown.sh

echo "Setting up cron job for auto-shutdown..."
echo "*/10 * * * * /opt/auto-shutdown.sh" | crontab -

echo "Installing CloudWatch agent..."
yum install -y amazon-cloudwatch-agent

cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOL'
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/deployment.log",
                        "log_group_name": "/aws/ec2/deployment",
                        "log_stream_name": "{instance_id}-deployment"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/userdata",
                        "log_stream_name": "{instance_id}-userdata"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "JavaApp/EC2",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOL

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

echo "Setting up environment variables..."
cat >> /home/ec2-user/.bashrc << 'EOL'
export JAVA_HOME=/usr/lib/jvm/java-17-amazon-corretto.x86_64
export PATH=$PATH:$JAVA_HOME/bin:/usr/local/bin
export AWS_DEFAULT_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
EOL

echo "Setting correct permissions..."
chown -R ec2-user:ec2-user /home/ec2-user/deployment
chown ec2-user:ec2-user /home/ec2-user/.bashrc

echo "Creating deployment status file..."
echo "READY" > /tmp/deployment-status
chown ec2-user:ec2-user /tmp/deployment-status

echo "User data script completed at $(date)"
echo "Instance is ready for deployment execution" 