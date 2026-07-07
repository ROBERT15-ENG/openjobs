#!/bin/bash
# JobSeek - Quick Start Script
# Usage: ./run_jobseek.sh

echo "Starting JobSeek Server..."

# Check and install dependencies if needed
pip install flask flask-limiter flask-cors requests werkzeug ezdxf fpdf 2>/dev/null

# Start the server
cd "$(dirname "$0")/api"
python3 server.py