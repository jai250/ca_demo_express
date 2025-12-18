#!/bin/bash

# Install and configure Nginx locally
#
# Usage: ./install_nginx.sh <domain_name>
#
# For remote EC2 installation, use the Python scripts instead:
# python3 install_nginx.py --host <EC2_IP> --username <ec2-user|ubuntu> --key-file <path-to-key.pem>
# python3 setup_nginx.py <domain> --host <EC2_IP> --username <ec2-user|ubuntu> --key-file <path-to-key.pem>
#
# This script installs and configures Nginx on Ubuntu/Debian systems locally.

DOMAIN_NAME=$1

# Install and Configure Nginx
sudo apt update
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

CONFIG_FILE="/etc/nginx/sites-available/${DOMAIN_NAME}"
sudo tee $CONFIG_FILE > /dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf $CONFIG_FILE /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx