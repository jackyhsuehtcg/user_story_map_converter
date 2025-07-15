#!/bin/bash

# User Story Map Converter - Quick Installation Script
# 
# Prerequisites: Python 3.8+, pip, Node.js, npm
# Usage: ./quick_install.sh

set -e

echo "🚀 Installing User Story Map Converter..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Install markmap-cli
echo "🗺️ Installing markmap-cli..."
npm install -g markmap-cli

# Create directories
echo "📁 Creating directories..."
mkdir -p logs exports temp static

# Create config template
if [ ! -f "config.yaml" ]; then
    echo "⚙️ Creating config.yaml template..."
    cat > config.yaml << 'EOF'
app:
  secret_key: "change-this-secret-key"

lark:
  app_id: "your-lark-app-id"
  app_secret: "your-lark-app-secret"
  timeout: 30
  max_retries: 3
  requests_per_minute: 100

logging:
  level: "INFO"

jira:
  base_url: "https://your-jira-domain.com"
  issue_url_template: "{base_url}/browse/{tcg_number}"
  link_target: "_blank"
  link_title_template: "Open {tcg_number} in JIRA"
EOF
fi

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your Lark API credentials"
echo "2. Run: python3 app.py"
echo "3. Open: http://localhost:8889"