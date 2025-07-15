#!/bin/bash

# User Story Map Converter - Ubuntu Installation Script
# 
# Prerequisites:
# - Python 3.8+ with pip
# - Node.js with npm
# - Git
#
# Usage: ./install_ubuntu.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    local required_version="3.8"
    local python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
        return 0
    else
        return 1
    fi
}

# Main installation function
main() {
    log_info "Starting User Story Map Converter installation..."
    
    # Check prerequisites
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command_exists python3; then
        log_error "Python 3 is not installed. Please install Python 3.8+ first."
        exit 1
    fi
    
    if ! check_python_version; then
        log_error "Python 3.8+ is required. Current version: $(python3 --version)"
        exit 1
    fi
    
    log_success "Python 3 is available: $(python3 --version)"
    
    # Check pip
    if ! command_exists pip3; then
        log_error "pip3 is not installed. Please install pip3 first."
        exit 1
    fi
    
    log_success "pip3 is available: $(pip3 --version)"
    
    # Check Node.js
    if ! command_exists node; then
        log_error "Node.js is not installed. Please install Node.js first."
        exit 1
    fi
    
    log_success "Node.js is available: $(node --version)"
    
    # Check npm
    if ! command_exists npm; then
        log_error "npm is not installed. Please install npm first."
        exit 1
    fi
    
    log_success "npm is available: $(npm --version)"
    
    # Check Git
    if ! command_exists git; then
        log_error "Git is not installed. Please install Git first."
        exit 1
    fi
    
    log_success "Git is available: $(git --version)"
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    
    # Upgrade pip
    log_info "Upgrading pip..."
    python3 -m pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        log_info "Installing from requirements.txt..."
        pip3 install -r requirements.txt
        log_success "Python dependencies installed successfully"
    else
        log_error "requirements.txt not found. Are you in the correct directory?"
        exit 1
    fi
    
    # Install markmap-cli globally
    log_info "Installing markmap-cli globally..."
    npm install -g markmap-cli
    
    # Verify markmap-cli installation
    if command_exists markmap; then
        log_success "markmap-cli installed successfully: $(markmap --version)"
    else
        log_error "markmap-cli installation failed"
        exit 1
    fi
    
    # Create necessary directories
    log_info "Creating necessary directories..."
    mkdir -p logs
    mkdir -p exports
    mkdir -p temp
    mkdir -p static
    
    log_success "Directories created successfully"
    
    # Create config.yaml from template if it doesn't exist
    if [ ! -f "config.yaml" ]; then
        log_info "Creating config.yaml template..."
        cat > config.yaml << 'EOF'
app:
  secret_key: "your-secret-key-change-this-in-production"

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
        log_success "config.yaml template created"
        log_warning "Please edit config.yaml with your actual Lark API credentials"
    else
        log_info "config.yaml already exists, skipping template creation"
    fi
    
    # Set permissions
    log_info "Setting file permissions..."
    chmod +x app.py
    chmod -R 755 logs exports temp static
    
    # Test installation
    log_info "Testing installation..."
    
    # Test Python imports
    python3 -c "
import flask
import requests
import yaml
print('✓ Python dependencies working')
"
    
    # Test markmap-cli
    markmap --help > /dev/null 2>&1
    log_success "markmap-cli is working"
    
    # Installation complete
    log_success "Installation completed successfully!"
    
    echo ""
    echo "=========================================="
    echo "Next steps:"
    echo "1. Edit config.yaml with your Lark API credentials"
    echo "2. Run the application: python3 app.py"
    echo "3. Open your browser to http://localhost:8889"
    echo "=========================================="
    echo ""
    
    # Optional: Show config.yaml location
    echo "Config file location: $(pwd)/config.yaml"
    echo "Please update the following settings:"
    echo "  - lark.app_id: Your Lark App ID"
    echo "  - lark.app_secret: Your Lark App Secret"
    echo "  - app.secret_key: A secure secret key"
    echo "  - jira.base_url: Your JIRA instance URL (if using JIRA integration)"
}

# Check if script is run from correct directory
if [ ! -f "app.py" ]; then
    log_error "app.py not found. Please run this script from the project root directory."
    exit 1
fi

# Run main function
main "$@"