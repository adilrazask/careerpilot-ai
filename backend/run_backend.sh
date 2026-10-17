#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

export PYTHONPATH=.
echo "Starting CareerPilot AI Backend on http://127.0.0.1:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
