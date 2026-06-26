import os
import json
import sqlite3
from typing import Any, Optional
from datetime import datetime

# Detect environment variables
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

firebase_configured = False
db_firestore = None

if FIREBASE_PROJECT_ID or GOOGLE_APPLICATION_CREDENTIALS:
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

# SQLite Fallback Setup
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
    conn.commit()
    conn.close()

if not firebase_configured:
    init_sqlite_db()
    print(f"Civio Database: SQLite initialized at {SQLITE_DB_PATH}")

# Core DB Operations Interface
def save_document(collection: str, doc_id: str, data: dict) -> str:
    if firebase_configured and db_firestore:
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
        conn.commit()
        conn.close()
        return doc_id

def get_document(collection: str, doc_id: str) -> Optional[dict]:
    if firebase_configured and db_firestore:
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
    if firebase_configured and db_firestore:
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
    if firebase_configured and db_firestore:
        docs = db_firestore.collection(collection).stream()
        return [doc.to_dict() for doc in docs]
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT data FROM {collection}")
        rows = cursor.fetchall()
        conn.close()
        return [json.loads(row[0]) for row in rows]
