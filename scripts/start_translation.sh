#!/bin/bash
# Translation Backend Startup Script
# Run this to start local translation servers

echo "=== Hardwareless AI Translation Stack ==="

# Check for optional dependencies
echo "Checking dependencies..."

# MTranServer check
if command -v npx &> /dev/null; then
    echo "✓ npx available (for MTranServer)"
else
    echo "✗ npx not found - install Node.js for MTranserver"
fi

# Python deps check
python3 -c "import aiohttp" 2>/dev/null && echo "✓ aiohttp" || echo "✗ aiohttp missing - pip install aiohttp"
python3 -c "import ctranslate2" 2>/dev/null && echo "✓ ctranslate2" || echo "✗ ctranslate2 missing - pip install ctranslate2"

echo ""
echo "Starting translation services..."
echo ""

# Option 1: Start MTranServer in background (if not already running)
# npx mtranserver@latest &

# Option 2: Start LibreTranslate (if not already running)
# docker run -it -p 5000:5000 --rm libretranslate/libretranslate

echo "To start services manually:"
echo "  MTranServer:  npx mtranserver@latest"
echo "  LibreTranslate: docker run -it -p 5000:5000 --rm libretranslate/libretranslate"
echo ""
echo "Then initialize in Python:"
echo "  from core_engine.translation import setup_translation_backends"
echo "  registry = setup_translation_backends()"