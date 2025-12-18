#!/usr/bin/env python3
import subprocess
import sys
import argparse
import paramiko
import os
from io import StringIO

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

def get_nginx_config_path(ssh, domain, os_type):
    """Get the appropriate Nginx configuration path based on OS."""
    if os_type in ['ubuntu', 'debian']:
        return f"/etc/nginx/sites-available/{domain}"
    elif os_type in ['amzn', 'amazon']:
        return f"/etc/nginx/conf.d/{domain}.conf"
    else:
        # Default to Ubuntu-style
        return f"/etc/nginx/sites-available/{domain}"

def get_nginx_enabled_path(ssh, domain, os_type):
    """Get the appropriate Nginx enabled site path based on OS."""
    if os_type in ['ubuntu', 'debian']:
        return f"/etc/nginx/sites-enabled/{domain}"
    elif os_type in ['amzn', 'amazon']:
        # Amazon Linux uses conf.d directly, no symlink needed
        return None
    else:
        return f"/etc/nginx/sites-enabled/{domain}"

def write_remote_file(ssh, remote_path, content, sudo=False):
    """Write content to a remote file."""
    try:
        # Create a temporary file locally
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp') as tmp_file:
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Use SFTP to transfer the file
            sftp = ssh.open_sftp()
            
            if sudo:
                # For sudo, we need to write to a temp location first, then move with sudo
                temp_remote_path = f"/tmp/{os.path.basename(remote_path)}.tmp"
                sftp.put(tmp_file_path, temp_remote_path)
                sftp.close()
                
                # Move with sudo
                execute_remote_command(ssh, f"mv {temp_remote_path} {remote_path}", sudo=True)
                execute_remote_command(ssh, f"chmod 644 {remote_path}", sudo=True)
            else:
                sftp.put(tmp_file_path, remote_path)
                sftp.close()
            
            return True
        finally:
            # Clean up local temp file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        print(f"Error writing remote file: {e}")
        return False

def setup_nginx_remote(host, username, key_file, domain, port=22, app_port=3000):
    """Setup Nginx configuration on a remote EC2 instance."""
    ssh = None
    try:
        ssh = get_ssh_client(host, username, key_file, port)
        
        # Detect OS
        os_type = detect_os(ssh)
        print(f"Detected OS: {os_type}")
        
        # Generate Nginx configuration
        config_content = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://localhost:{app_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        
        # Get appropriate paths
        config_path = get_nginx_config_path(ssh, domain, os_type)
        enabled_path = get_nginx_enabled_path(ssh, domain, os_type)
        
        print(f"Creating Nginx config at {config_path}...")
        if not write_remote_file(ssh, config_path, config_content, sudo=True):
            raise Exception("Failed to write Nginx configuration file")
        
        # Enable the site (for Ubuntu/Debian)
        if enabled_path:
            print(f"Enabling site at {enabled_path}...")
            # Remove existing symlink if it exists
            execute_remote_command(ssh, f"rm -f {enabled_path}", sudo=True)
            # Create symlink
            if not execute_remote_command(ssh, f"ln -s {config_path} {enabled_path}", sudo=True):
                raise Exception("Failed to enable Nginx site")
        
        print("Testing Nginx configuration...")
        if not execute_remote_command(ssh, "nginx -t", sudo=True):
            raise Exception("Nginx configuration test failed")
        
        print("Reloading Nginx...")
        if not execute_remote_command(ssh, "systemctl reload nginx", sudo=True):
            # Try restart if reload fails
            execute_remote_command(ssh, "systemctl restart nginx", sudo=True)
        
        print(f"Nginx setup for {domain} completed successfully!")
        
    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)
    finally:
        if ssh:
            ssh.close()

def setup_nginx_local(domain):
    """Setup Nginx configuration locally (original functionality)."""
    config_path = f"/etc/nginx/sites-available/{domain}"
    enabled_link = f"/etc/nginx/sites-enabled/{domain}"

    config_content = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    try:
        print(f"Creating Nginx config for {domain}...")
        with open(config_path, 'w') as f:
            f.write(config_content)

        print("Enabling site...")
        if os.path.exists(enabled_link):
            subprocess.run(['sudo', 'rm', enabled_link], check=True)
        subprocess.run(['sudo', 'ln', '-s', config_path, enabled_link], check=True)

        print("Testing Nginx configuration...")
        subprocess.run(['sudo', 'nginx', '-t'], check=True)

        print("Restarting Nginx...")
        subprocess.run(['sudo', 'systemctl', 'restart', 'nginx'], check=True)

        print(f"Nginx setup for {domain} completed.")
    except subprocess.CalledProcessError as e:
        print(f"Error during setup: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Setup Nginx configuration on local or remote EC2 instance')
    parser.add_argument('domain', type=str, help='Domain name for Nginx configuration')
    parser.add_argument('--host', type=str, help='EC2 instance hostname or IP address')
    parser.add_argument('--username', type=str, help='SSH username (e.g., ec2-user, ubuntu)')
    parser.add_argument('--key-file', type=str, help='Path to SSH private key file (.pem)')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--app-port', type=int, default=3000, help='Application port to proxy (default: 3000)')
    
    args = parser.parse_args()
    
    if args.host and args.username and args.key_file:
        # Remote setup
        if not os.path.exists(args.key_file):
            print(f"Error: Key file '{args.key_file}' not found.")
            sys.exit(1)
        setup_nginx_remote(args.host, args.username, args.key_file, args.domain, args.port, args.app_port)
    else:
        # Local setup
        print("No remote connection parameters provided. Setting up Nginx locally...")
        setup_nginx_local(args.domain)
