#!/bin/bash

set -e

# Check .env exists
if [ ! -f .env ]; then
  echo "WARNING: .env file not found. Copy .env.example to .env and update with your configuration."
fi

# Create logs directory if missing
mkdir -p logs

# Create data/pending_lore directory if missing
mkdir -p data/pending_lore

# Check Python is available
if ! command -v python3 &> /dev/null; then
  echo "ERROR: python3 is not installed or not in PATH"
  exit 1
fi

# Check Node.js is available
if ! command -v node &> /dev/null; then
  echo "ERROR: node is not installed or not in PATH"
  exit 1
fi

# Install Python dependencies silently
echo "Installing Python dependencies..."
pip install -q fastapi uvicorn psutil requests

# Install Node dependencies if node_modules missing
if [ ! -d node_modules ]; then
  echo "Installing Node dependencies..."
  npm install -q --only=production
fi

# Start with pm2
echo "Starting Gargoyle Packy V2.0.0..."
pm2 start ecosystem.config.cjs

# Save pm2 state
pm2 save

# Print status
echo ""
echo "Services started successfully!"
pm2 status
