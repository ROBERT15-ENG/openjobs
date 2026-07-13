#!/bin/bash
# OpenJobs - Quick Start Script

set -e
cd "$(dirname "$0")"

echo "Installing dependencies..."
pip install -r requirements.txt -q

if [ ! -f jobs.db ]; then
  echo "Initializing database..."
  python3 scripts/init_db.py
fi

echo "Starting OpenJobs server on http://localhost:5700"
cd api
python3 server.py
