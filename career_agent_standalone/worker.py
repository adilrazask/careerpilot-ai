"""Entrypoint for the CareerPilot background worker."""
from automation import worker_loop, run_once
if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(description="CareerPilot AI background automation")
    p.add_argument("--once", action="store_true", help="run one automation cycle and exit")
    args=p.parse_args()
    run_once() if args.once else worker_loop()
