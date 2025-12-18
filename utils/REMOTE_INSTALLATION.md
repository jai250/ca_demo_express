# Remote EC2 Installation Guide

This guide explains how to use the custom action files to install Docker and Nginx on remote AWS EC2 instances.

## Prerequisites

1. **Python 3.6+** installed on your local machine
2. **SSH key pair** (.pem file) for accessing your EC2 instance
3. **EC2 instance** running (Amazon Linux 2 or Ubuntu)
4. **Network access** to your EC2 instance (SSH port 22 open in security group)

## Installation

Install required Python dependencies:

```bash
pip3 install -r requirements.txt
```

## Usage

### Install Docker on Remote EC2 Instance

```bash
python3 install_docker.py \
  --host <EC2_PUBLIC_IP_OR_DNS> \
  --username <ec2-user|ubuntu> \
  --key-file <path-to-your-key.pem> \
  [--port 22]
```

**Examples:**

For Amazon Linux 2:
```bash
python3 install_docker.py --host 54.123.45.67 --username ec2-user --key-file ~/.ssh/my-key.pem
```

For Ubuntu:
```bash
python3 install_docker.py --host ec2-54-123-45-67.compute-1.amazonaws.com --username ubuntu --key-file ~/.ssh/my-key.pem
```

### Install Nginx on Remote EC2 Instance

```bash
python3 install_nginx.py \
  --host <EC2_PUBLIC_IP_OR_DNS> \
  --username <ec2-user|ubuntu> \
  --key-file <path-to-your-key.pem> \
  [--port 22]
```

**Examples:**

For Amazon Linux 2:
```bash
python3 install_nginx.py --host 54.123.45.67 --username ec2-user --key-file ~/.ssh/my-key.pem
```

For Ubuntu:
```bash
python3 install_nginx.py --host ec2-54-123-45-67.compute-1.amazonaws.com --username ubuntu --key-file ~/.ssh/my-key.pem
```

### Setup Nginx Configuration on Remote EC2 Instance

```bash
python3 setup_nginx.py <domain_name> \
  --host <EC2_PUBLIC_IP_OR_DNS> \
  --username <ec2-user|ubuntu> \
  --key-file <path-to-your-key.pem> \
  [--port 22] \
  [--app-port 3000]
```

**Examples:**

```bash
python3 setup_nginx.py example.com \
  --host 54.123.45.67 \
  --username ec2-user \
  --key-file ~/.ssh/my-key.pem \
  --app-port 3000
```

## Complete Workflow Example

Here's a complete example of setting up Docker and Nginx on a new EC2 instance:

```bash
# 1. Set variables
export EC2_HOST="54.123.45.67"
export EC2_USER="ec2-user"  # or "ubuntu" for Ubuntu instances
export KEY_FILE="~/.ssh/my-key.pem"

# 2. Install Docker
python3 install_docker.py \
  --host $EC2_HOST \
  --username $EC2_USER \
  --key-file $KEY_FILE

# 3. Install Nginx
python3 install_nginx.py \
  --host $EC2_HOST \
  --username $EC2_USER \
  --key-file $KEY_FILE

# 4. Setup Nginx configuration
python3 setup_nginx.py example.com \
  --host $EC2_HOST \
  --username $EC2_USER \
  --key-file $KEY_FILE \
  --app-port 3000
```

## Local Installation (Fallback)

If you don't provide remote connection parameters, the scripts will attempt local installation:

```bash
# Local Docker installation
python3 install_docker.py

# Local Nginx installation
python3 install_nginx.py

# Local Nginx setup
python3 setup_nginx.py example.com
```

## Supported Operating Systems

The scripts automatically detect and support:
- **Ubuntu/Debian** - Uses `apt` package manager
- **Amazon Linux 2** - Uses `yum` package manager
- **Other Linux distributions** - Attempts generic installation

## Troubleshooting

### Connection Issues

1. **Check SSH key permissions:**
   ```bash
   chmod 400 your-key.pem
   ```

2. **Verify security group allows SSH (port 22):**
   - Check AWS Console → EC2 → Security Groups
   - Ensure inbound rule allows SSH from your IP

3. **Test SSH connection manually:**
   ```bash
   ssh -i your-key.pem ec2-user@your-ec2-ip
   ```

### Installation Failures

1. **Check instance has internet access** (for package downloads)
2. **Verify instance has sufficient disk space**
3. **Check instance logs** for detailed error messages:
   ```bash
   ssh -i your-key.pem ec2-user@your-ec2-ip
   sudo journalctl -xe
   ```

### Permission Issues

- The scripts use `sudo` for privileged operations
- Ensure the SSH user has sudo privileges on the EC2 instance
- For Amazon Linux 2, `ec2-user` has sudo by default
- For Ubuntu, the default user has sudo by default

## Security Notes

1. **Never commit your `.pem` key files** to version control
2. **Use IAM roles** for EC2 instances when possible instead of access keys
3. **Restrict security group rules** to specific IPs when possible
4. **Rotate SSH keys** regularly in production environments

## Script Parameters

### Common Parameters

- `--host`: EC2 instance public IP or DNS name (required for remote)
- `--username`: SSH username (`ec2-user` for Amazon Linux, `ubuntu` for Ubuntu)
- `--key-file`: Path to SSH private key file (.pem)
- `--port`: SSH port (default: 22)

### setup_nginx.py Specific

- `domain`: Domain name for Nginx configuration (positional argument)
- `--app-port`: Port where your application runs (default: 3000)

