"""
Entry point for the Clinic Reception Chatbot.

Usage:
    python run.py           # start server on http://127.0.0.1:5000
    python run.py --seed    # (re)create DB with sample data
"""
import argparse
import os
import sys

from app import create_app
from database.models import init_db
from database.seed import seed_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Clinic Reception Chatbot")
    parser.add_argument("--seed", action="store_true", help="Reset DB and seed sample data")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    db_path = os.path.join(os.path.dirname(__file__), "clinic.db")

    if args.seed or not os.path.exists(db_path):
        print("[setup] Initialising database...")
        init_db(db_path)
        print("[setup] Seeding sample data...")
        seed_all(db_path)
        print("[setup] Done.")

    app = create_app(db_path=db_path)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
