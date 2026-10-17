#!/bin/bash
# CareerPilot AI Unified Starter Script
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=========================================================="
echo " Starting CareerPilot AI Autonomous Platform "
echo "=========================================================="

echo "1. Initializing and checking Backend..."
cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Run database migration / init
PYTHONPATH=. python -c "from app.database_init import init_db; init_db()"
echo "Database initialized at data/careerpilot.db"

echo ""
echo "To run the services concurrently, run the following in separate terminal windows:"
echo "--------------------------------------------------------------------------------"
echo "  Terminal 1 (Backend API):   cd $ROOT_DIR/backend && ./run_backend.sh"
echo "  Terminal 2 (Worker Queue):  cd $ROOT_DIR/backend && ./run_worker.sh"
echo "  Terminal 3 (Frontend SPA):  cd $ROOT_DIR/frontend && ./run_frontend.sh"
echo "--------------------------------------------------------------------------------"
echo "  FastAPI Swagger Docs:       http://localhost:8000/docs"
echo "  Frontend Dashboard:         http://localhost:5173"
echo "=========================================================="
