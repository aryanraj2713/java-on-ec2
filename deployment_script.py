#!/usr/bin/env python3

import os
import subprocess
import sys
import time
import signal
import logfire
from pathlib import Path
import argparse
from secrets_manager import get_secret
from typing import Optional

logfire.configure()

class JavaAppDeployer:
    def __init__(self, repo_url: str, target_dir: str = "./app", java_port: int = 9000):
        self.repo_url = repo_url
        self.target_dir = Path(target_dir)
        self.java_port = java_port
        self.java_process = None
        
    def setup_ssh_key(self) -> bool:
        with logfire.span("setup_ssh_key") as span:
            try:
                logfire.info("Retrieving SSH key from AWS Secrets Manager")
                
                ssh_key = get_secret(
                    secret_name=os.environ.get("SSH_SECRET_NAME", "java-app-ssh-key"),
                    region_name=os.environ.get("AWS_REGION", "eu-north-1")
                )
                
                if not ssh_key:
                    logfire.error("No SSH key retrieved from Secrets Manager")
                    return False
                
                ssh_dir = Path.home() / ".ssh"
                ssh_dir.mkdir(mode=0o700, exist_ok=True)
                
                ssh_key_path = ssh_dir / "deploy_key"
                
                logfire.debug("Writing SSH key to file")
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
                
                span.set_attribute("ssh_key_setup", True)
                logfire.info("SSH key setup completed successfully")
                return True
                
            except Exception as e:
                span.record_exception(e)
                logfire.error("Failed to setup SSH key", error_message=str(e), exc_info=e)
                return False
    
    def clone_repository(self) -> bool:
        with logfire.span("clone_repository", repo_url=self.repo_url, target_dir=str(self.target_dir)) as span:
            try:
                logfire.info("Starting repository clone", repo_url=self.repo_url, target_dir=str(self.target_dir))
                
                if self.target_dir.exists():
                    logfire.info("Removing existing directory")
                    subprocess.run(["rm", "-rf", str(self.target_dir)], check=True)
                
                logfire.debug("Executing git clone command")
                result = subprocess.run([
                    "git", "clone", self.repo_url, str(self.target_dir)
                ], capture_output=True, text=True, check=True)
                
                span.set_attribute("clone_successful", True)
                span.set_attribute("git_output_length", len(result.stdout))
                
                logfire.info("Repository cloned successfully", repo_url=self.repo_url, output_length=len(result.stdout))
                return True
                
            except subprocess.CalledProcessError as e:
                span.set_attribute("clone_successful", False)
                span.record_exception(e)
                
                logfire.error("Git clone failed", repo_url=self.repo_url, return_code=e.returncode, stderr=e.stderr, exc_info=e)
                return False
            
            except Exception as e:
                span.record_exception(e)
                logfire.error("Unexpected error during clone", repo_url=self.repo_url, error_message=str(e), exc_info=e)
                return False
    
    def verify_jar_exists(self) -> bool:
        with logfire.span("verify_jar_exists") as span:
            jar_path = self.target_dir / "build" / "libs" / "project.jar"
            
            logfire.debug("Checking for JAR file", jar_path=str(jar_path))
            
            if jar_path.exists():
                jar_size = jar_path.stat().st_size
                span.set_attribute("jar_exists", True)
                span.set_attribute("jar_size", jar_size)
                
                logfire.info("JAR file found", jar_path=str(jar_path), jar_size=jar_size)
                return True
            else:
                span.set_attribute("jar_exists", False)
                logfire.error("JAR file not found", jar_path=str(jar_path))
                return False
    
    def start_java_process(self) -> bool:
        with logfire.span("start_java_process", port=self.java_port) as span:
            try:
                jar_path = self.target_dir / "build" / "libs" / "project.jar"
                
                logfire.info("Starting Java application", jar_path=str(jar_path), port=self.java_port)
                
                self.java_process = subprocess.Popen([
                    "java", "-jar", str(jar_path)
                ], cwd=str(self.target_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                time.sleep(2)
                
                if self.java_process.poll() is None:
                    span.set_attribute("java_started", True)
                    span.set_attribute("java_pid", self.java_process.pid)
                    
                    logfire.info("Java application started successfully", pid=self.java_process.pid, port=self.java_port)
                    return True
                else:
                    stdout, stderr = self.java_process.communicate()
                    span.set_attribute("java_started", False)
                    
                    logfire.error("Java application failed to start", 
                                return_code=self.java_process.returncode,
                                stdout=stdout.decode() if stdout else "",
                                stderr=stderr.decode() if stderr else "")
                    return False
                    
            except Exception as e:
                span.record_exception(e)
                logfire.error("Failed to start Java application", error_message=str(e), exc_info=e)
                return False
    
    def stop_java_process(self):
        with logfire.span("stop_java_process") as span:
            if self.java_process:
                logfire.info("Stopping Java application", pid=self.java_process.pid)
                
                self.java_process.terminate()
                
                try:
                    self.java_process.wait(timeout=10)
                    span.set_attribute("graceful_shutdown", True)
                    logfire.info("Java application stopped gracefully")
                    
                except subprocess.TimeoutExpired:
                    logfire.warning("Forcing Java application to stop")
                    self.java_process.kill()
                    self.java_process.wait()
                    span.set_attribute("graceful_shutdown", False)
    
    def deploy(self) -> bool:
        with logfire.span("deploy_application") as span:
            logfire.info("Starting deployment process")
            
            try:
                if not self.setup_ssh_key():
                    logfire.error("SSH key setup failed")
                    return False
                
                if not self.clone_repository():
                    logfire.error("Repository clone failed")
                    return False
                
                if not self.verify_jar_exists():
                    logfire.error("JAR verification failed")
                    return False
                
                if not self.start_java_process():
                    logfire.error("Java process start failed")
                    return False
                
                span.set_attribute("deployment_successful", True)
                logfire.info("Deployment completed successfully")
                return True
                
            except Exception as e:
                span.record_exception(e)
                logfire.error("Deployment failed with unexpected error", error_message=str(e), exc_info=e)
                return False

def signal_handler(signum, frame):
    with logfire.span("signal_handler", signal=signum):
        logfire.info("Received shutdown signal", signal=signum)
        
        if 'deployer' in globals():
            deployer.stop_java_process()
        
        logfire.info("Application shutdown completed")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Deploy Java application with Logfire logging')
    parser.add_argument('repo_url', help='SSH URL of the Git repository')
    parser.add_argument('--target-dir', default='./app', help='Target directory for cloning')
    parser.add_argument('--port', type=int, default=9000, help='Java application port')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    args = parser.parse_args()
    
    with logfire.span("main_execution") as span:
        logfire.info("Starting deployment script", repo_url=args.repo_url, target_dir=args.target_dir, port=args.port, daemon_mode=args.daemon)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        global deployer
        deployer = JavaAppDeployer(args.repo_url, args.target_dir, args.port)
        
        if deployer.deploy():
            if args.daemon:
                logfire.info("Running in daemon mode")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logfire.info("Received interrupt signal")
            else:
                logfire.info("Deployment completed - process running", pid=deployer.java_process.pid if deployer.java_process else None)
        else:
            span.set_attribute("deployment_failed", True)
            logfire.error("Deployment failed")
            sys.exit(1)

if __name__ == "__main__":
    main() 