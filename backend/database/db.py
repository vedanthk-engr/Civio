import os
import json
import sqlite3
from typing import Any, Optional
from datetime import datetime

# Detect environment variables
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
DATABASE_URL = os.environ.get("DATABASE_URL")

firebase_configured = False
postgres_configured = False
db_firestore = None
pg_pool = None

# 1. Try PostgreSQL Connection if configured
if DATABASE_URL:
    try:
        import psycopg
        from psycopg_pool import ConnectionPool
        pg_pool = ConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=10, open=True)
        postgres_configured = True
        print("Civio Database: Initialized PostgreSQL Connection Pool.")
        
        # Ensure schema
        with pg_pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    id VARCHAR PRIMARY KEY,
                    category VARCHAR,
                    status VARCHAR,
                    ward VARCHAR,
                    severity INTEGER,
                    data TEXT
                )
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_orders (
                    id VARCHAR PRIMARY KEY,
                    issue_id VARCHAR,
                    status VARCHAR,
                    data TEXT
                )
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR PRIMARY KEY,
                    role VARCHAR,
                    data TEXT
                )
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS quests (
                    id VARCHAR PRIMARY KEY,
                    data TEXT
                )
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id VARCHAR PRIMARY KEY,
                    issue_id VARCHAR,
                    timestamp VARCHAR,
                    data TEXT
                )
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS spam_issues (
                    id VARCHAR PRIMARY KEY,
                    timestamp VARCHAR,
                    data TEXT
                )
                """)
                conn.commit()
        print("Civio Database: PostgreSQL tables validated/created successfully.")
    except Exception as e:
        print(f"Civio Database: Failed to initialize PostgreSQL: {e}. Falling back...")
        postgres_configured = False

# 2. Try Firebase Firestore fallback if PostgreSQL is not active
if not postgres_configured and (FIREBASE_PROJECT_ID or GOOGLE_APPLICATION_CREDENTIALS):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            if GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
                cred = credentials.Certificate(GOOGLE_APPLICATION_CREDENTIALS)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
        db_firestore = firestore.client()
        firebase_configured = True
        print("Civio Database: Initialized Firebase Firestore.")
    except Exception as e:
        print(f"Civio Database: Failed to initialize Firebase Firestore: {e}. Falling back to SQLite.")

# 3. SQLite Fallback Setup (if neither Postgres nor Firebase is active)
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "civio.db")

def init_sqlite_db():
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # Create tables mirroring collections
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id TEXT PRIMARY KEY,
        category TEXT,
        status TEXT,
        ward TEXT,
        severity INTEGER,
        data TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS work_orders (
        id TEXT PRIMARY KEY,
        issue_id TEXT,
        status TEXT,
        data TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        role TEXT,
        data TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quests (
        id TEXT PRIMARY KEY,
        data TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        issue_id TEXT,
        timestamp TEXT,
        data TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spam_issues (
        id TEXT PRIMARY KEY,
        timestamp TEXT,
        data TEXT
    )
    """)
    conn.commit()
    conn.close()

if not postgres_configured and not firebase_configured:
    init_sqlite_db()
    print(f"Civio Database: SQLite initialized at {SQLITE_DB_PATH}")

# Core DB Operations Interface
def save_document(collection: str, doc_id: str, data: dict) -> str:
    if postgres_configured and pg_pool:
        data_str = json.dumps(data, default=str)
        with pg_pool.connection() as conn:
            with conn.cursor() as cursor:
                if collection == "issues":
                    cursor.execute(
                        "INSERT INTO issues (id, category, status, ward, severity, data) VALUES (%s, %s, %s, %s, %s, %s) "
                        "ON CONFLICT (id) DO UPDATE SET category=EXCLUDED.category, status=EXCLUDED.status, ward=EXCLUDED.ward, severity=EXCLUDED.severity, data=EXCLUDED.data",
                        (doc_id, data.get("category"), data.get("status"), data.get("location", {}).get("ward"), data.get("aiAnalysis", {}).get("severityScore", 1), data_str)
                    )
                elif collection == "work_orders":
                    cursor.execute(
                        "INSERT INTO work_orders (id, issue_id, status, data) VALUES (%s, %s, %s, %s) "
                        "ON CONFLICT (id) DO UPDATE SET issue_id=EXCLUDED.issue_id, status=EXCLUDED.status, data=EXCLUDED.data",
                        (doc_id, data.get("issueId"), data.get("status"), data_str)
                    )
                elif collection == "users":
                    cursor.execute(
                        "INSERT INTO users (id, role, data) VALUES (%s, %s, %s) "
                        "ON CONFLICT (id) DO UPDATE SET role=EXCLUDED.role, data=EXCLUDED.data",
                        (doc_id, data.get("role"), data_str)
                    )
                elif collection == "quests":
                    cursor.execute(
                        "INSERT INTO quests (id, data) VALUES (%s, %s) "
                        "ON CONFLICT (id) DO UPDATE SET data=EXCLUDED.data",
                        (doc_id, data_str)
                    )
                elif collection == "audit_logs":
                    cursor.execute(
                        "INSERT INTO audit_logs (id, issue_id, timestamp, data) VALUES (%s, %s, %s, %s) "
                        "ON CONFLICT (id) DO UPDATE SET issue_id=EXCLUDED.issue_id, timestamp=EXCLUDED.timestamp, data=EXCLUDED.data",
                        (doc_id, data.get("issueId"), data.get("timestamp"), data_str)
                    )
                elif collection == "spam_issues":
                    cursor.execute(
                        "INSERT INTO spam_issues (id, timestamp, data) VALUES (%s, %s, %s) "
                        "ON CONFLICT (id) DO UPDATE SET timestamp=EXCLUDED.timestamp, data=EXCLUDED.data",
                        (doc_id, data.get("timestamp"), data_str)
                    )
                conn.commit()
        return doc_id
    elif firebase_configured and db_firestore:
        db_firestore.collection(collection).document(doc_id).set(data)
        return doc_id
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        data_str = json.dumps(data, default=str)
        if collection == "issues":
            cursor.execute(
                "INSERT OR REPLACE INTO issues (id, category, status, ward, severity, data) VALUES (?, ?, ?, ?, ?, ?)",
                (doc_id, data.get("category"), data.get("status"), data.get("location", {}).get("ward"), data.get("aiAnalysis", {}).get("severityScore", 1), data_str)
            )
        elif collection == "work_orders":
            cursor.execute(
                "INSERT OR REPLACE INTO work_orders (id, issue_id, status, data) VALUES (?, ?, ?, ?)",
                (doc_id, data.get("issueId"), data.get("status"), data_str)
            )
        elif collection == "users":
            cursor.execute(
                "INSERT OR REPLACE INTO users (id, role, data) VALUES (?, ?, ?)",
                (doc_id, data.get("role"), data_str)
            )
        elif collection == "quests":
            cursor.execute(
                "INSERT OR REPLACE INTO quests (id, data) VALUES (?, ?)",
                (doc_id, data_str)
            )
        elif collection == "audit_logs":
            cursor.execute(
                "INSERT OR REPLACE INTO audit_logs (id, issue_id, timestamp, data) VALUES (?, ?, ?, ?)",
                (doc_id, data.get("issueId"), data.get("timestamp"), data_str)
            )
        elif collection == "spam_issues":
            cursor.execute(
                "INSERT OR REPLACE INTO spam_issues (id, timestamp, data) VALUES (?, ?, ?)",
                (doc_id, data.get("timestamp"), data_str)
            )
        conn.commit()
        conn.close()
        return doc_id

def get_document(collection: str, doc_id: str) -> Optional[dict]:
    if postgres_configured and pg_pool:
        with pg_pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT data FROM {collection} WHERE id = %s", (doc_id,))
                row = cursor.fetchone()
                return json.loads(row[0]) if row else None
    elif firebase_configured and db_firestore:
        doc = db_firestore.collection(collection).document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT data FROM {collection} WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None

def update_document(collection: str, doc_id: str, updates: dict) -> bool:
    if postgres_configured and pg_pool:
        doc = get_document(collection, doc_id)
        if not doc:
            return False
        # Deep merge updates
        def merge(target, source):
            for k, v in source.items():
                if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                    merge(target[k], v)
                else:
                    target[k] = v
        merge(doc, updates)
        save_document(collection, doc_id, doc)
        return True
    elif firebase_configured and db_firestore:
        try:
            db_firestore.collection(collection).document(doc_id).update(updates)
            return True
        except Exception:
            return False
    else:
        doc = get_document(collection, doc_id)
        if not doc:
            return False
        
        # Deep merge updates
        def merge(target, source):
            for k, v in source.items():
                if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                    merge(target[k], v)
                else:
                    target[k] = v
        merge(doc, updates)
        save_document(collection, doc_id, doc)
        return True

def list_documents(collection: str) -> list[dict]:
    if postgres_configured and pg_pool:
        with pg_pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT data FROM {collection}")
                rows = cursor.fetchall()
                return [json.loads(row[0]) for row in rows]
    elif firebase_configured and db_firestore:
        docs = db_firestore.collection(collection).stream()
        return [doc.to_dict() for doc in docs]
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT data FROM {collection}")
        rows = cursor.fetchall()
        conn.close()
        return [json.loads(row[0]) for row in rows]
