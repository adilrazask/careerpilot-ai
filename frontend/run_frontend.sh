#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Starting CareerPilot AI Frontend Dashboard on http://localhost:5173..."
exec npm run dev
