#!/usr/bin/env python3

import os
import subprocess
import sys
import time
import signal
from pathlib import Path
import argparse
from secrets_manager_simple import get_secret
from typing import Optional

class JavaAppDeployer:
    def __init__(self, repo_url: str, target_dir: str = "./app", java_port: int = 9000):
        self.repo_url = repo_url
        self.target_dir = Path(target_dir)
        self.java_port = java_port
        self.java_process = None
        
    def setup_ssh_key(self) -> bool:
        try:
            print("Retrieving SSH key from AWS Secrets Manager")
            
            ssh_key = get_secret(
                secret_name=os.environ.get("SSH_SECRET_NAME", "java-app-ssh-key"),
                region_name=os.environ.get("AWS_REGION", "us-east-1")
            )
            
            if not ssh_key:
                print("ERROR: No SSH key retrieved from Secrets Manager")
                return False
            
            ssh_dir = Path.home() / ".ssh"
            ssh_dir.mkdir(mode=0o700, exist_ok=True)
            
            ssh_key_path = ssh_dir / "deploy_key"
            
            print("Writing SSH key to file")
            with open(ssh_key_path, 'w') as f:
                f.write(ssh_key)
            
            ssh_key_path.chmod(0o600)
            
            ssh_config = ssh_dir / "config"
            config_content = f"""
Host github.com
    HostName github.com
    User git
    IdentityFile {ssh_key_path}
    StrictHostKeyChecking no
"""
            
            with open(ssh_config, 'w') as f:
                f.write(config_content)
            
            print("SSH key setup completed successfully")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to setup SSH key: {e}")
            return False
    
    def clone_repository(self) -> bool:
        try:
            print(f"Starting repository clone: {self.repo_url} -> {self.target_dir}")
            
            if self.target_dir.exists():
                print("Removing existing directory")
                subprocess.run(["rm", "-rf", str(self.target_dir)], check=True)
            
            print("Executing git clone command")
            result = subprocess.run([
                "git", "clone", self.repo_url, str(self.target_dir)
            ], capture_output=True, text=True, check=True)
            
            print(f"Repository cloned successfully: {len(result.stdout)} bytes output")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Git clone failed: {e.returncode} - {e.stderr}")
            return False
        
        except Exception as e:
            print(f"ERROR: Unexpected error during clone: {e}")
            return False
    
    def verify_jar_exists(self) -> bool:
        jar_path = self.target_dir / "build" / "libs" / "project.jar"
        
        print(f"Checking for JAR file: {jar_path}")
        
        if jar_path.exists():
            jar_size = jar_path.stat().st_size
            print(f"JAR file found: {jar_path} ({jar_size} bytes)")
            return True
        else:
            print(f"ERROR: JAR file not found: {jar_path}")
            return False
    
    def start_java_process(self) -> bool:
        try:
            jar_path = self.target_dir / "build" / "libs" / "project.jar"
            
            print(f"Starting Java application: {jar_path} on port {self.java_port}")
            
            self.java_process = subprocess.Popen([
                "java", "-jar", str(jar_path)
            ], cwd=str(self.target_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            time.sleep(2)
            
            if self.java_process.poll() is None:
                print(f"Java application started successfully (PID: {self.java_process.pid})")
                return True
            else:
                stdout, stderr = self.java_process.communicate()
                print(f"ERROR: Java application failed to start")
                print(f"Return code: {self.java_process.returncode}")
                print(f"STDOUT: {stdout.decode() if stdout else 'None'}")
                print(f"STDERR: {stderr.decode() if stderr else 'None'}")
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to start Java application: {e}")
            return False
    
    def stop_java_process(self):
        if self.java_process:
            print(f"Stopping Java application (PID: {self.java_process.pid})")
            
            self.java_process.terminate()
            
            try:
                self.java_process.wait(timeout=10)
                print("Java application stopped gracefully")
                
            except subprocess.TimeoutExpired:
                print("WARNING: Forcing Java application to stop")
                self.java_process.kill()
                self.java_process.wait()
    
    def deploy(self) -> bool:
        print("Starting deployment process")
        
        try:
            if not self.setup_ssh_key():
                print("ERROR: SSH key setup failed")
                return False
            
            if not self.clone_repository():
                print("ERROR: Repository clone failed")
                return False
            
            if not self.verify_jar_exists():
                print("ERROR: JAR verification failed")
                return False
            
            if not self.start_java_process():
                print("ERROR: Java process start failed")
                return False
            
            print("Deployment completed successfully")
            return True
            
        except Exception as e:
            print(f"ERROR: Deployment failed with unexpected error: {e}")
            return False

def signal_handler(signum, frame):
    print(f"Received shutdown signal: {signum}")
    
    if 'deployer' in globals():
        deployer.stop_java_process()
    
    print("Application shutdown completed")
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Deploy Java application (simplified version)')
    parser.add_argument('repo_url', help='SSH URL of the Git repository')
    parser.add_argument('--target-dir', default='./app', help='Target directory for cloning')
    parser.add_argument('--port', type=int, default=9000, help='Java application port')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    args = parser.parse_args()
    
    print(f"Starting deployment script")
    print(f"Repository: {args.repo_url}")
    print(f"Target directory: {args.target_dir}")
    print(f"Port: {args.port}")
    print(f"Daemon mode: {args.daemon}")
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    global deployer
    deployer = JavaAppDeployer(args.repo_url, args.target_dir, args.port)
    
    if deployer.deploy():
        if args.daemon:
            print("Running in daemon mode")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Received interrupt signal")
        else:
            pid = deployer.java_process.pid if deployer.java_process else None
            print(f"Deployment completed - process running (PID: {pid})")
    else:
        print("ERROR: Deployment failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 