#!/bin/bash
# Hardwareless AI Installer
# Run: curl -fsSL https://hardwareless.ai/install.sh | bash

set -e

echo "🧠 Installing Hardwareless AI..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3.10+ required. Install from python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info[1])')
if [ "$PYTHON_VERSION" -lt 10 ]; then
    echo "Python 3.10+ required. Current: 3.$PYTHON_VERSION"
    exit 1
fi

# Create venv
python3 -m venv ~/.hardwareless
source ~/.hardwareless/bin/activate

# Install
pip install --upgrade pip
pip install hardwareless-ai

# Add to PATH
SHELL_RC="$HOME/.bashrc"
if [ "$(uname)" = "Darwin" ]; then
    SHELL_RC="$HOME/.zshrc"
fi

if ! grep -q "hardwareless" "$SHELL_RC" 2>/dev/null; then
    echo 'alias hardwareless="~/.hardwareless/bin/python3 -m hardwareless"' >> "$SHELL_RC"
    echo "✓ Added 'hardwareless' alias to $SHELL_RC"
fi

echo ""
echo "✅ Hardwareless AI installed!"
echo ""
echo "Commands:"
echo "  hardwareless run           # Start gateway"
echo "  hardwareless chat          # Interactive chat"
echo "  hardwareless translate    # CLI translation"
echo "  hardwareless skills       # List skills"
echo ""
echo "Or use directly: python3 -m hardwareless run"