#!/bin/bash

# User Story Map Converter - Development Setup Script
# 
# This script sets up a development environment with additional tools
# Prerequisites: Python 3.8+, pip, Node.js, npm
# Usage: ./dev_setup.sh

set -e

echo "🛠️ Setting up development environment..."

# Install Python dependencies including dev tools
echo "📦 Installing Python dependencies (including dev tools)..."
pip3 install -r requirements.txt

# Install additional development tools
echo "🔧 Installing development tools..."
pip3 install --upgrade \
    flake8 \
    black \
    pytest \
    pytest-cov

# Install markmap-cli
echo "🗺️ Installing markmap-cli..."
npm install -g markmap-cli

# Create development directories
echo "📁 Creating development directories..."
mkdir -p logs exports temp static
mkdir -p tests docs

# Create config template for development
if [ ! -f "config.yaml" ]; then
    echo "⚙️ Creating development config.yaml..."
    cat > config.yaml << 'EOF'
app:
  secret_key: "dev-secret-key-not-for-production"

lark:
  app_id: "your-lark-app-id"
  app_secret: "your-lark-app-secret"
  timeout: 30
  max_retries: 3
  requests_per_minute: 100

logging:
  level: "DEBUG"  # Debug level for development

jira:
  base_url: "https://jira.tc-gaming.co/jira"
  issue_url_template: "{base_url}/browse/{tcg_number}"
  link_target: "_blank"
  link_title_template: "Open {tcg_number} in JIRA"
EOF
fi

# Create pre-commit hook (optional)
if [ -d ".git" ]; then
    echo "🔍 Setting up pre-commit hook..."
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run flake8 on Python files
echo "Running flake8..."
flake8 app.py core/ tools/ --max-line-length=88 --ignore=E203,W503

# Run tests
echo "Running tests..."
python3 -m pytest tests/ -v

echo "Pre-commit checks passed!"
EOF
    chmod +x .git/hooks/pre-commit
fi

# Create development scripts
echo "📝 Creating development scripts..."

# Create run_dev.sh
cat > run_dev.sh << 'EOF'
#!/bin/bash
# Development server with auto-reload
echo "🚀 Starting development server..."
export FLASK_ENV=development
export FLASK_DEBUG=1
python3 app.py
EOF
chmod +x run_dev.sh

# Create test.sh
cat > test.sh << 'EOF'
#!/bin/bash
# Run tests with coverage
echo "🧪 Running tests with coverage..."
python3 -m pytest tests/ -v --cov=core --cov=app --cov-report=html --cov-report=term
echo "📊 Coverage report generated in htmlcov/"
EOF
chmod +x test.sh

# Create format.sh
cat > format.sh << 'EOF'
#!/bin/bash
# Format code with black
echo "🎨 Formatting code with black..."
black app.py core/ tools/ --line-length=88
echo "✅ Code formatted!"
EOF
chmod +x format.sh

# Create lint.sh
cat > lint.sh << 'EOF'
#!/bin/bash
# Lint code with flake8
echo "🔍 Linting code with flake8..."
flake8 app.py core/ tools/ --max-line-length=88 --ignore=E203,W503
echo "✅ Linting complete!"
EOF
chmod +x lint.sh

echo "✅ Development environment setup complete!"
echo ""
echo "Development tools installed:"
echo "  • flake8 - Code linting"
echo "  • black - Code formatting"
echo "  • pytest - Testing framework"
echo "  • pytest-cov - Coverage reporting"
echo ""
echo "Development scripts created:"
echo "  • ./run_dev.sh - Start development server"
echo "  • ./test.sh - Run tests with coverage"
echo "  • ./format.sh - Format code"
echo "  • ./lint.sh - Lint code"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your Lark API credentials"
echo "2. Run: ./run_dev.sh"
echo "3. Open: http://localhost:8889"