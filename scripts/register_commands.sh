#!/bin/bash
set -e

if [ -z "$DISCORD_TOKEN" ] || [ -z "$DISCORD_CLIENT_ID" ]; then
  # Try loading from .env
  if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -E 'DISCORD_TOKEN|DISCORD_CLIENT_ID' | xargs)
  fi
fi

if [ -z "$DISCORD_TOKEN" ]; then
  echo "ERROR: DISCORD_TOKEN not set. Check your .env file."
  exit 1
fi

if [ -z "$DISCORD_CLIENT_ID" ]; then
  echo "ERROR: DISCORD_CLIENT_ID not set. Check your .env file."
  exit 1
fi

echo "Registering slash commands..."
node src/bot/commands/register.js

echo "Commands registered. They'll be live in Discord within 1 hour."
