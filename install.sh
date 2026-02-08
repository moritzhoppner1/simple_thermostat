#!/bin/bash
# Simple Thermostat Installation Script
# Usage: curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/simple_thermostat/main/install.sh | bash

set -e

GITHUB_REPO="YOUR_USERNAME/simple_thermostat"
BRANCH="main"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/config}"
CUSTOM_COMPONENTS_DIR="$HA_CONFIG_DIR/custom_components"

echo "=========================================="
echo "Simple Thermostat Installation"
echo "=========================================="
echo ""

# Check if Home Assistant config directory exists
if [ ! -d "$HA_CONFIG_DIR" ]; then
    echo "❌ Error: Home Assistant config directory not found at $HA_CONFIG_DIR"
    echo "   Set HA_CONFIG_DIR environment variable if using different location"
    echo "   Example: HA_CONFIG_DIR=/home/homeassistant/.homeassistant ./install.sh"
    exit 1
fi

echo "✓ Found Home Assistant config at: $HA_CONFIG_DIR"

# Create custom_components directory if it doesn't exist
if [ ! -d "$CUSTOM_COMPONENTS_DIR" ]; then
    echo "Creating custom_components directory..."
    mkdir -p "$CUSTOM_COMPONENTS_DIR"
fi

echo "✓ Custom components directory: $CUSTOM_COMPONENTS_DIR"
echo ""

# Download and extract
echo "Downloading Simple Thermostat from GitHub..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Try wget first, fall back to curl
if command -v wget &> /dev/null; then
    wget -q "https://github.com/$GITHUB_REPO/archive/refs/heads/$BRANCH.tar.gz" -O simple_thermostat.tar.gz
elif command -v curl &> /dev/null; then
    curl -sSL "https://github.com/$GITHUB_REPO/archive/refs/heads/$BRANCH.tar.gz" -o simple_thermostat.tar.gz
else
    echo "❌ Error: Neither wget nor curl found. Please install one of them."
    exit 1
fi

echo "✓ Downloaded"
echo ""

# Extract
echo "Extracting files..."
tar xzf simple_thermostat.tar.gz

# Find the extracted directory
EXTRACTED_DIR=$(find . -maxdepth 1 -type d -name "simple_thermostat-*" | head -n 1)

if [ -z "$EXTRACTED_DIR" ]; then
    echo "❌ Error: Could not find extracted directory"
    exit 1
fi

echo "✓ Extracted"
echo ""

# Copy integration files
echo "Installing integration..."

# Remove old installation if exists
if [ -d "$CUSTOM_COMPONENTS_DIR/simple_thermostat" ]; then
    echo "  Removing old installation..."
    rm -rf "$CUSTOM_COMPONENTS_DIR/simple_thermostat"
fi

# Copy new files
cp -r "$EXTRACTED_DIR/custom_components/simple_thermostat" "$CUSTOM_COMPONENTS_DIR/"

echo "✓ Installed to: $CUSTOM_COMPONENTS_DIR/simple_thermostat"
echo ""

# Cleanup
cd -
rm -rf "$TEMP_DIR"

# Show version
VERSION=$(grep -o '"version": "[^"]*"' "$CUSTOM_COMPONENTS_DIR/simple_thermostat/manifest.json" | cut -d'"' -f4)

echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "Installed: Simple Thermostat v$VERSION"
echo ""
echo "Next steps:"
echo "1. Restart Home Assistant"
echo "2. Add configuration to configuration.yaml"
echo "3. (Optional) Add custom card resource:"
echo "   Settings → Dashboards → Resources"
echo "   URL: /simple_thermostat/simple-thermostat-card.js"
echo "   Type: JavaScript Module"
echo ""
echo "Documentation:"
echo "  https://github.com/$GITHUB_REPO/blob/$BRANCH/README.md"
echo ""
echo "Configuration example:"
echo "  https://github.com/$GITHUB_REPO/blob/$BRANCH/configuration.yaml.example"
echo ""
