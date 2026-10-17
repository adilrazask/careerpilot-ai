#!/bin/bash
set -e
cd "$(dirname "$0")"

source .venv/bin/activate
export PYTHONPATH=.
echo "Starting CareerPilot AI Durable Background Worker..."
exec python worker.py
