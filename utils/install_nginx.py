#!/usr/bin/env python3
import subprocess
import sys
import argparse
import paramiko
import os

def get_ssh_client(host, username, key_file, port=22):
    """Create and return an SSH client connected to the EC2 instance."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Load the private key
        key = paramiko.RSAKey.from_private_key_file(key_file)
        
        print(f"Connecting to {username}@{host}:{port}...")
        ssh.connect(hostname=host, username=username, pkey=key, port=port, timeout=30)
        print("Connected successfully!")
        return ssh
    except Exception as e:
        print(f"Error connecting to EC2 instance: {e}")
        sys.exit(1)

def execute_remote_command(ssh, command, sudo=False):
    """Execute a command on the remote EC2 instance."""
    try:
        if sudo:
            command = f"sudo {command}"
        
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        if output:
            print(output)
        if error and exit_status != 0:
            print(f"Error: {error}", file=sys.stderr)
        
        return exit_status == 0
    except Exception as e:
        print(f"Error executing command '{command}': {e}")
        return False

def detect_os(ssh):
    """Detect the operating system on the remote EC2 instance."""
    stdin, stdout, stderr = ssh.exec_command("cat /etc/os-release | grep -E '^ID=' | cut -d'=' -f2 | tr -d '\"'")
    os_id = stdout.read().decode('utf-8').strip().lower()
    return os_id

def install_nginx_remote(host, username, key_file, port=22):
    """Install Nginx on a remote EC2 instance."""
    ssh = None
    try:
        ssh = get_ssh_client(host, username, key_file, port)
        
        # Detect OS
        os_type = detect_os(ssh)
        print(f"Detected OS: {os_type}")
        
        if os_type in ['ubuntu', 'debian']:
            print("Updating package list...")
            if not execute_remote_command(ssh, "apt update", sudo=True):
                raise Exception("Failed to update package list")
            
            print("Installing Nginx...")
            if not execute_remote_command(ssh, "apt install -y nginx", sudo=True):
                raise Exception("Failed to install Nginx")
        
        elif os_type in ['amzn', 'amazon']:
            print("Updating package list...")
            execute_remote_command(ssh, "yum update -y", sudo=True)
            
            print("Installing Nginx...")
            if not execute_remote_command(ssh, "yum install -y nginx", sudo=True):
                raise Exception("Failed to install Nginx")
        
        else:
            print(f"Warning: Unsupported OS type '{os_type}'. Attempting generic installation...")
            execute_remote_command(ssh, "apt update || yum update -y", sudo=True)
            execute_remote_command(ssh, "apt install -y nginx || yum install -y nginx", sudo=True)
        
        print("Starting Nginx service...")
        if not execute_remote_command(ssh, "systemctl start nginx", sudo=True):
            raise Exception("Failed to start Nginx service")
        
        print("Enabling Nginx service...")
        execute_remote_command(ssh, "systemctl enable nginx", sudo=True)
        
        print("Checking Nginx status...")
        execute_remote_command(ssh, "systemctl status nginx", sudo=True)
        
        print("Nginx installation completed successfully!")
        
    except Exception as e:
        print(f"Error during installation: {e}")
        sys.exit(1)
    finally:
        if ssh:
            ssh.close()

def install_nginx_local():
    """Install Nginx locally (original functionality)."""
    try:
        print("Updating package list...")
        subprocess.run(['sudo', 'apt', 'update'], check=True)

        print("Installing Nginx...")
        subprocess.run(['sudo', 'apt', 'install', '-y', 'nginx'], check=True)

        print("Starting Nginx service...")
        subprocess.run(['sudo', 'systemctl', 'start', 'nginx'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'nginx'], check=True)

        print("Nginx installation completed.")
    except subprocess.CalledProcessError as e:
        print(f"Error during installation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Install Nginx on local or remote EC2 instance')
    parser.add_argument('--host', type=str, help='EC2 instance hostname or IP address')
    parser.add_argument('--username', type=str, help='SSH username (e.g., ec2-user, ubuntu)')
    parser.add_argument('--key-file', type=str, help='Path to SSH private key file (.pem)')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default: 22)')
    
    args = parser.parse_args()
    
    if args.host and args.username and args.key_file:
        # Remote installation
        if not os.path.exists(args.key_file):
            print(f"Error: Key file '{args.key_file}' not found.")
            sys.exit(1)
        install_nginx_remote(args.host, args.username, args.key_file, args.port)
    else:
        # Local installation
        print("No remote connection parameters provided. Installing Nginx locally...")
        install_nginx_local()
