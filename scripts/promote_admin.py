#!/usr/bin/env python3
"""Promote a user to admin by email. Run locally against jobs.db."""

import argparse
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(ROOT, "jobs.db")


def main():
    parser = argparse.ArgumentParser(description="Set role=admin for a user email")
    parser.add_argument("email", help="User email (must already be registered)")
    parser.add_argument(
        "--db",
        default=os.environ.get("DATABASE_URL", DEFAULT_DB),
        help="SQLite database path (default: jobs.db or DATABASE_URL)",
    )
    args = parser.parse_args()
    email = args.email.strip().lower()
    if not email:
        print("email required", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT id, name, role FROM users WHERE lower(email) = ?", (email,))
    row = cur.fetchone()
    if not row:
        print(f"No user found for {email}", file=sys.stderr)
        sys.exit(1)
    conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()
    print(f"OK: {row['name']} (id={row['id']}) was {row['role']!r} → admin")


if __name__ == "__main__":
    main()
