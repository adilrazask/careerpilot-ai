#!/bin/bash
# CareerPilot AI Single-Command Unified Starter
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=========================================================="
echo " Starting CareerPilot AI Autonomous Platform (Local Mode)"
echo "=========================================================="

cleanup() {
    echo ""
    echo "Stopping all CareerPilot services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Free up ports if lingering from previous run
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# 1. Start Backend in background
echo "1. Starting Backend API & Autonomous Worker on port 8000..."
cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

export PYTHONPATH=.
export RUN_WORKER_IN_APP=true
python3 -c "from app.database_init import init_db; init_db()"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
until curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; do
    sleep 1
done
echo "✅ Backend API is live at http://localhost:8000"

# 2. Start Frontend in background
echo "2. Starting Frontend Dashboard on port 5173..."
cd "$ROOT_DIR/frontend"
npm run dev -- --host --port 5173 &
FRONTEND_PID=$!

# Wait for frontend to be ready
until curl -s http://localhost:5173 >/dev/null 2>&1; do
    sleep 1
done
echo "✅ Frontend Dashboard is live at http://localhost:5173"

echo ""
echo "=========================================================="
echo " 🧭 CareerPilot AI is RUNNING SUCCESSFULLY!"
echo " 👉 URL: http://localhost:5173"
echo " 👉 API Docs: http://localhost:8000/docs"
echo " Press Ctrl+C anytime to stop."
echo "=========================================================="
echo ""

# Automatically open in browser on Mac
if command -v open >/dev/null 2>&1; then
    open "http://localhost:5173"
fi

# Keep script running to keep background services alive
wait
