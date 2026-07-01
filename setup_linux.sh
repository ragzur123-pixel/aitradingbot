#!/bin/bash
# AiTradingBot: Institutional Linux Deployment Script
# Targets: Ubuntu 22.04+ with Real-Time (RT) Kernel optimization

echo "--- 🏗️ INITIALIZING INSTITUTIONAL DEPLOYMENT ---"

# 1. System Updates
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Python & Docker
sudo apt-get install -y python3-pip python3-venv docker.io docker-compose

# 3. Optimization: Increase File Descriptor Limits
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# 4. Create Service Directory
mkdir -p ~/aitradingbot/logs
cd ~/aitradingbot

# 5. Setup Systemd Watchdog (Persistence)
sudo tee /etc/systemd/system/aitradingbot.service <<EOF
[Unit]
Description=AiTradingBot: Heartbeat & Orchestrator
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(which python3) master_orchestrator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 6. Start Ollama (Background)
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
sleep 10
ollama pull llama3.1

echo "--- ✅ DEPLOYMENT READY ---"
echo "1. Update your .env file with POLYGON_API_KEY."
echo "2. Run: sudo systemctl enable --now aitradingbot"
