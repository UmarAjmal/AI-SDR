"""
Codenter AI SDR Platform — Supabase Database Migration Runner
Strictly applies the Developer Product Specification v1.0 Section 12 Schema to Supabase.
"""
import os
import sys
import asyncio
from pathlib import Path
import asyncpg
from dotenv import load_dotenv

# Load .env file from project root if present
load_dotenv(Path(__file__).parent.parent / ".env")

# Verified connection details
DB_HOST = os.getenv("SUPABASE_DB_HOST", "aws-1-ap-northeast-2.pooler.supabase.com")
DB_PORT = int(os.getenv("SUPABASE_DB_PORT", "5432"))
DB_USER = os.getenv("SUPABASE_DB_USER", "postgres.eunavicktaghgtkxuryy")
DB_PASS = os.getenv("SUPABASE_DB_PASS", "AISDR@#!!@#123")
DB_NAME = os.getenv("SUPABASE_DB_NAME", "postgres")

SCHEMA_FILE = Path(__file__).parent / "supabase_schema.sql"

EXPECTED_TABLES = [
    "users",
    "workspaces",
    "workspace_members",
    "business_profiles",
    "knowledge_documents",
    "knowledge_chunks",
    "website_scans",
    "crm_connections",
    "crm_leads",
    "lead_enrichment",
    "campaigns",
    "campaign_steps",
    "campaign_leads",
    "email_accounts",
    "email_threads",
    "email_messages",
    "ai_responses",
    "conversation_events",
    "calendar_connections",
    "appointments",
    "suppression_list",
    "unsubscribe_events",
    "usage_events",
    "audit_logs"
]

async def run_migration():
    print("=" * 70)
    print("Codenter AI SDR — Supabase Schema Deployment")
    print("=" * 70)
    print(f"Connecting to: {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}...")

    if not SCHEMA_FILE.exists():
        print(f"ERROR: Schema file not found at: {SCHEMA_FILE}")
        sys.exit(1)

    sql_content = SCHEMA_FILE.read_text(encoding="utf-8")
    print(f"Loaded schema SQL: {len(sql_content)} bytes ({len(sql_content.splitlines())} lines)")

    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            ssl="require",
            timeout=30.0
        )
        print(" Connected to Supabase PostgreSQL successfully!")
        
        # Check PG Version
        version = await conn.fetchval("SELECT version();")
        print(f"Server version: {version}")

        # Execute Schema
        print("\nExecuting schema DDL (Extensions, ENUMs, 24 Tables, Indexes, Vectors)...")
        await conn.execute(sql_content)
        print(" Schema execution completed successfully!")

        # Verification: Check all tables exist
        print("\nVerifying tables in database...")
        rows = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        existing_tables = set(r["table_name"] for r in rows)

        all_passed = True
        print("-" * 50)
        print(f"{'Table Name':<30} | {'Status':<15}")
        print("-" * 50)
        for tbl in EXPECTED_TABLES:
            if tbl in existing_tables:
                print(f"{tbl:<30} |  EXISTS")
            else:
                print(f"{tbl:<30} | ❌ MISSING")
                all_passed = False
        print("-" * 50)

        # Check extensions
        ext_rows = await conn.fetch("SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector');")
        print("\nInstalled Extensions:")
        for r in ext_rows:
            print(f" - {r['extname']} (v{r['extversion']})")

        # Summary
        if all_passed:
            print(f"\n ALL {len(EXPECTED_TABLES)} TABLES CONFIRMED IN SUPABASE!")
        else:
            print(f"\n⚠️ Some tables were missing. Check output above.")

        await conn.close()
        return all_passed

    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
