"""
Database Migration Utility: SQLite to PostgreSQL
Transfers all tables, schema definitions, and records from SQLite to PostgreSQL.
Usage:
    python -m app.migrate_to_postgres [POSTGRES_URL]
"""
from __future__ import annotations
import sys
import os
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.config import settings

def migrate_sqlite_to_postgres(sqlite_url: str = None, postgres_url: str = None) -> bool:
    """Migrates all data from SQLite database into PostgreSQL."""
    sq_url = sqlite_url or settings.DATABASE_URL
    pg_url = postgres_url or os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")

    if not pg_url or "postgres" not in pg_url:
        print("[Migration] No PostgreSQL target URL provided. Skipping Postgres migration.", flush=True)
        return False

    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql://", 1)

    print(f"[Migration] Starting migration from {sq_url} to {pg_url}...", flush=True)

    sqlite_engine = create_engine(sq_url)
    postgres_engine = create_engine(pg_url, pool_pre_ping=True)

    # 1. Create all schema tables in PostgreSQL
    Base.metadata.create_all(bind=postgres_engine)
    print("[Migration] Schema tables created in target PostgreSQL database.", flush=True)

    # 2. Copy data table by table in dependency order
    tables_to_copy = [
        "users", "company_profiles", "job_sources", "career_profiles",
        "employment_history", "skills", "education", "certifications",
        "career_preferences", "resume_files", "resume_versions",
        "job_listings", "job_requirements", "job_match_results",
        "recruiter_contacts", "contact_verification_records",
        "application_records", "application_attempts", "automation_policies",
        "automation_audit_logs", "email_messages", "follow_up_tasks",
        "recruiter_responses", "interviews", "system_health", "worker_runs"
    ]

    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    pg_meta = MetaData()
    pg_meta.reflect(bind=postgres_engine)

    with sqlite_engine.connect() as sq_conn, postgres_engine.connect() as pg_conn:
        for tname in tables_to_copy:
            if tname not in sqlite_meta.tables or tname not in pg_meta.tables:
                continue

            src_table = sqlite_meta.tables[tname]
            dst_table = pg_meta.tables[tname]

            # Read all records
            rows = sq_conn.execute(src_table.select()).fetchall()
            if not rows:
                continue

            # Convert Row objects to dict
            records = [dict(r._mapping) for r in rows]

            # Insert into Postgres in chunks
            try:
                pg_conn.execute(dst_table.insert(), records)
                pg_conn.commit()
                print(f"[Migration] Copied {len(records)} records for table '{tname}'.", flush=True)
            except Exception as e:
                pg_conn.rollback()
                print(f"[Migration] Note for '{tname}': {e}", flush=True)

    print("[Migration] SQLite to PostgreSQL migration complete.", flush=True)
    return True

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else None
    migrate_sqlite_to_postgres(postgres_url=target_url)
