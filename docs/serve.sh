#!/bin/bash

# Build and serve ptools documentation
# Usage: ./serve.sh [port]

set -e

PORT=${1:-8000}
DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Building documentation..."
cd "$DOCS_DIR"

# Clean previous build
rm -rf _build/html

# Build documentation
/Library/Frameworks/Python.framework/Versions/3.12/bin/sphinx-build -b html . _build/html

if [ $? -eq 0 ]; then
    echo "Documentation built successfully!"
    echo "Opening browser..."
    
    # Start local server and open browser
    cd _build/html
    echo "Serving documentation at http://localhost:$PORT"
    echo "Press Ctrl+C to stop the server"
    
    # Open browser after a brief delay
    (sleep 2 && python3 -m webbrowser "http://localhost:$PORT") &
    
    # Serve the documentation
    python3 -m http.server $PORT
else
    echo "Build failed!"
    exit 1
fi
