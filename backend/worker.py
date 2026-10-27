"""
Standalone durable background worker for CareerPilot AI.
Runs continuously independent of the web browser.
"""
from __future__ import annotations
import sys
import time
import signal
import argparse
from datetime import datetime, timezone

from app.database import SessionLocal
from app.database_init import init_db
from app.models import AutomationPolicy, WorkerRun
from app.services.scheduler import DurableScheduler, WORKER_ID

stop_requested = False

def handle_signal(sig, frame):
    global stop_requested
    print(f"\n[Worker] Termination signal {sig} received. Performing graceful shutdown...", flush=True)
    stop_requested = True

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def run_single_cycle():
    init_db()
    db = SessionLocal()
    try:
        print(f"[Worker {WORKER_ID}] Starting single autonomous cycle...", flush=True)
        res = DurableScheduler.execute_autonomous_cycle(db)
        print(f"[Worker {WORKER_ID}] Cycle result: {res}", flush=True)
        return res
    finally:
        db.close()

def worker_loop(stop_event=None):
    global stop_requested
    init_db()
    print(f"==================================================", flush=True)
    print(f" CareerPilot AI Background Worker Initialized", flush=True)
    print(f" Worker ID: {WORKER_ID}", flush=True)
    print(f" Press Ctrl+C to stop gracefully.", flush=True)
    print(f"==================================================", flush=True)

    def is_stopped():
        return stop_requested or (stop_event is not None and stop_event.is_set())

    while not is_stopped():
        db = SessionLocal()
        try:
            # Heartbeat & check policy
            DurableScheduler.register_or_update_heartbeat(db, current_task="IDLE_CHECK")
            policy = db.query(AutomationPolicy).filter_by(id=1).first()

            if policy and not policy.pause_all_automation:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Executing scheduled autonomous cycle...", flush=True)
                res = DurableScheduler.execute_autonomous_cycle(db)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle finished: {res.get('status')} - {res.get('summary', {})}", flush=True)
                
                # Interval sleep
                interval_secs = max(30, (policy.search_interval_minutes or 240) * 60)
            else:
                interval_secs = 30 # Check again in 30s if paused

        except Exception as e:
            print(f"[Worker Error] Unhandled exception in cycle: {e}", file=sys.stderr, flush=True)
            interval_secs = 60
        finally:
            db.close()

        # Sleep in small slices to respond promptly to signals
        elapsed = 0
        while elapsed < interval_secs and not is_stopped():
            time.sleep(2)
            elapsed += 2

    # Clean up worker run record on exit
    db = SessionLocal()
    try:
        run = db.query(WorkerRun).filter_by(worker_id=WORKER_ID).first()
        if run:
            run.status = "STOPPED"
            run.stopped_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
    print("[Worker] Shutdown complete.", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CareerPilot AI Background Worker")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    args = parser.parse_args()

    if args.once:
        run_single_cycle()
    else:
        worker_loop()
