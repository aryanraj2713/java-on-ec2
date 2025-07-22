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
            
            # Debug: List contents of cloned directory
            print(f"Contents of {self.target_dir}:")
            try:
                for item in self.target_dir.iterdir():
                    print(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
                
                # Check specifically for gradlew
                gradlew_path = self.target_dir / "gradlew"
                print(f"gradlew exists: {gradlew_path.exists()}")
                if gradlew_path.exists():
                    print(f"gradlew permissions: {oct(gradlew_path.stat().st_mode)}")
            except Exception as e:
                print(f"Error listing directory contents: {e}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Git clone failed: {e.returncode} - {e.stderr}")
            return False
        
        except Exception as e:
            print(f"ERROR: Unexpected error during clone: {e}")
            return False
    
    def build_java_application(self) -> bool:
        try:
            print(f"Building Java application in: {self.target_dir}")
            
            # Find Java installation dynamically
            java_home = self._find_java_home()
            if not java_home:
                print("ERROR: Could not find Java installation")
                return False
            
            # Create environment with Java paths
            env = os.environ.copy()
            env["JAVA_HOME"] = java_home
            java_bin_path = f"{java_home}/bin"
            env["PATH"] = f"{java_bin_path}:{env.get('PATH', '')}"
            
            print(f"Using JAVA_HOME: {java_home}")
            print(f"Java PATH: {java_bin_path}")
            
            # Verify Java installation
            try:
                java_version_result = subprocess.run(
                    ["java", "-version"], 
                    env=env, 
                    capture_output=True, 
                    text=True
                )
                print(f"Java version check result: {java_version_result.returncode}")
                if java_version_result.stderr:
                    print(f"Java version output: {java_version_result.stderr[:200]}")
                if java_version_result.returncode != 0:
                    print("ERROR: Java version check failed")
                    return False
            except Exception as e:
                print(f"Java version check failed: {e}")
                return False
            
            # Check for gradlew first
            gradlew_path = self.target_dir / "gradlew"
            if gradlew_path.exists():
                print("Making gradlew executable")
                gradlew_path.chmod(0o755)
                absolute_gradlew_path = str(gradlew_path.absolute())
                print(f"Using gradlew at: {absolute_gradlew_path}")
                build_command = [absolute_gradlew_path, "build"]
            else:
                print("gradlew not found, trying system gradle")
                # Try to use system gradle as fallback
                try:
                    result = subprocess.run(["which", "gradle"], env=env, capture_output=True, text=True)
                    if result.returncode == 0:
                        print("Using system gradle")
                        build_command = ["gradle", "build"]
                    else:
                        print("ERROR: Neither gradlew nor system gradle found")
                        return False
                except Exception as e:
                    print(f"ERROR: Could not find gradle: {e}")
                    return False
            
            # Build the application
            print(f"Running build command: {' '.join(build_command)}")
            result = subprocess.run(
                build_command, 
                cwd=str(self.target_dir), 
                env=env,  # Pass the Java environment
                capture_output=True, 
                text=True, 
                check=True
            )
            
            print(f"Build completed successfully")
            print(f"Build output: {result.stdout[-500:] if result.stdout else 'None'}")  # Last 500 chars
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Build failed: {e.returncode}")
            print(f"STDOUT: {e.stdout if e.stdout else 'None'}")
            print(f"STDERR: {e.stderr if e.stderr else 'None'}")
            return False
        
        except Exception as e:
            print(f"ERROR: Unexpected error during build: {e}")
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
    
    def _find_java_home(self) -> str:
        """Find Java installation dynamically"""
        java_paths_to_try = [
            "/usr/lib/jvm/java-17-amazon-corretto",
            "/usr/lib/jvm/java-17-amazon-corretto.x86_64", 
            "/usr/lib/jvm/java-17-openjdk",
            "/usr/lib/jvm/java-17",
            "/usr/java/amazon-corretto-17",
            "/opt/java/openjdk"
        ]
        
        print("Searching for Java installation...")
        for path in java_paths_to_try:
            java_bin = f"{path}/bin/java"
            print(f"Checking: {java_bin}")
            try:
                if Path(java_bin).exists():
                    print(f"Found Java at: {path}")
                    return path
            except Exception as e:
                print(f"Error checking {java_bin}: {e}")
        
        # Fallback: try to find java in system PATH
        print("Java not found in standard locations, trying system PATH...")
        try:
            which_result = subprocess.run(["which", "java"], capture_output=True, text=True)
            print(f"which java result: {which_result.returncode}")
            print(f"which java stdout: '{which_result.stdout.strip()}'")
            print(f"which java stderr: '{which_result.stderr.strip()}'")
            
            if which_result.returncode == 0:
                java_binary_path = which_result.stdout.strip()
                print(f"Found java binary at: {java_binary_path}")
                # Try to determine JAVA_HOME from binary path
                if "/bin/java" in java_binary_path:
                    java_home = java_binary_path.replace("/bin/java", "")
                    print(f"Derived JAVA_HOME: {java_home}")
                    return java_home
                else:
                    print("Using system java without JAVA_HOME")
                    return None
        except Exception as e:
            print(f"Error finding java in PATH: {e}")
        
        # Additional debugging: check what's actually in /usr/lib/jvm/
        print("Debugging: Checking what's installed in /usr/lib/jvm/...")
        try:
            jvm_result = subprocess.run(["ls", "-la", "/usr/lib/jvm/"], capture_output=True, text=True)
            print(f"ls /usr/lib/jvm/ result: {jvm_result.returncode}")
            if jvm_result.stdout:
                print(f"JVM directory contents:\n{jvm_result.stdout}")
            if jvm_result.stderr:
                print(f"JVM directory error: {jvm_result.stderr}")
        except Exception as e:
            print(f"Error checking JVM directory: {e}")
        
        # Check if Java packages are installed
        print("Debugging: Checking installed Java packages...")
        try:
            rpm_result = subprocess.run(["rpm", "-qa", "|", "grep", "java"], shell=True, capture_output=True, text=True)
            print(f"Java packages found: {rpm_result.returncode}")
            if rpm_result.stdout:
                print(f"Installed Java packages:\n{rpm_result.stdout}")
        except Exception as e:
            print(f"Error checking Java packages: {e}")
        
        # Check userdata log to see if installation happened
        print("Debugging: Checking userdata log...")
        try:
            userdata_result = subprocess.run(["tail", "-20", "/var/log/user-data.log"], capture_output=True, text=True)
            if userdata_result.returncode == 0 and userdata_result.stdout:
                print(f"Last 20 lines of userdata log:\n{userdata_result.stdout}")
            else:
                print(f"Could not read userdata log: {userdata_result.returncode}")
        except Exception as e:
            print(f"Error reading userdata log: {e}")
        
        # Last resort: try to install Java directly
        print("Last resort: Attempting to install Java...")
        try:
            print("Installing Java 17 Amazon Corretto...")
            install_result = subprocess.run(
                ["sudo", "yum", "install", "-y", "java-17-amazon-corretto-headless"], 
                capture_output=True, 
                text=True
            )
            print(f"Java installation result: {install_result.returncode}")
            if install_result.stdout:
                print(f"Installation stdout: {install_result.stdout[-500:]}")  # Last 500 chars
            if install_result.stderr:
                print(f"Installation stderr: {install_result.stderr[-500:]}")  # Last 500 chars
            
            if install_result.returncode == 0:
                print("Java installation completed, re-checking...")
                # Re-run the search after installation
                for path in ["/usr/lib/jvm/java-17-amazon-corretto", "/usr/lib/jvm/java-17-amazon-corretto.x86_64"]:
                    java_bin = f"{path}/bin/java"
                    print(f"Re-checking: {java_bin}")
                    try:
                        if Path(java_bin).exists():
                            print(f"Found Java after installation at: {path}")
                            return path
                    except Exception as e:
                        print(f"Error re-checking {java_bin}: {e}")
                
                # Try system PATH again after installation
                try:
                    which_result = subprocess.run(["which", "java"], capture_output=True, text=True)
                    if which_result.returncode == 0:
                        java_binary_path = which_result.stdout.strip()
                        print(f"Found java in PATH after installation: {java_binary_path}")
                        if "/bin/java" in java_binary_path:
                            java_home = java_binary_path.replace("/bin/java", "")
                            print(f"Using JAVA_HOME after installation: {java_home}")
                            return java_home
                except Exception as e:
                    print(f"Error finding java in PATH after installation: {e}")
            else:
                print("Java installation failed")
                
        except Exception as e:
            print(f"Error during Java installation attempt: {e}")
        
        return None
    
    def start_java_process(self) -> bool:
        try:
            jar_path = self.target_dir / "build" / "libs" / "project.jar"
            
            print(f"Starting Java application: {jar_path} on port {self.java_port}")
            
            # Find Java installation (same logic as build)
            java_home = self._find_java_home()
            if not java_home:
                print("ERROR: Could not find Java installation for starting application")
                return False
            
            env = os.environ.copy()
            env["JAVA_HOME"] = java_home
            java_bin_path = f"{java_home}/bin"
            env["PATH"] = f"{java_bin_path}:{env.get('PATH', '')}"
            
            self.java_process = subprocess.Popen([
                "java", "-jar", str(jar_path)
            ], cwd=str(self.target_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            
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
            
            if not self.build_java_application():
                print("ERROR: Java application build failed")
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