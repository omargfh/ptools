#!/usr/bin/env bash

# Build PTools Documentation
# This script builds the Sphinx documentation for PTools

set -e  # Exit on any error

echo "Building PTools Documentation..."

# Check if we're in the docs directory
if [ ! -f "conf.py" ]; then
    echo "Error: Please run this script from the docs directory"
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing documentation dependencies..."
    pip install -r requirements.txt
fi

# Clean previous build
echo "Cleaning previous build..."
rm -rf _build/

# Build HTML documentation
echo "Building HTML documentation..."
sphinx-build -b html . _build/html

# Build PDF documentation (if needed)
# echo "Building PDF documentation..."
# sphinx-build -b latex . _build/latex
# cd _build/latex && make

echo "Documentation build complete!"
echo "HTML documentation is available at: _build/html/index.html"

# Open in browser if on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Opening documentation in browser..."
    open _build/html/index.html
fi
