#!/bin/bash

# User Story Map Converter - Uninstall Script
# 
# Usage: ./uninstall.sh

set -e

echo "🗑️ Uninstalling User Story Map Converter..."

# Remove Python packages
echo "📦 Removing Python packages..."
if [ -f "requirements.txt" ]; then
    pip3 uninstall -r requirements.txt -y || true
fi

# Remove markmap-cli
echo "🗺️ Removing markmap-cli..."
npm uninstall -g markmap-cli || true

# Remove runtime directories (with confirmation)
echo "📁 Cleaning up directories..."
read -p "Remove logs, exports, and temp directories? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf logs exports temp
    echo "✅ Directories removed"
else
    echo "⏭️ Directories kept"
fi

# Remove config file (with confirmation)
if [ -f "config.yaml" ]; then
    read -p "Remove config.yaml? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f config.yaml
        echo "✅ config.yaml removed"
    else
        echo "⏭️ config.yaml kept"
    fi
fi

echo "✅ Uninstall complete!"