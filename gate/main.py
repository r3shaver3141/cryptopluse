#!/usr/bin/env python3
"""CryptoPluse Data Gate — Production API server.

Run with:  uvicorn gate.main:app --host 0.0.0.0 --port 8080 --reload
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, Form
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSPACE = os.environ.get("CRYPTOPLUSE_WORKSPACE", "/Users/shaver/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
GATE_DIR = os.path.join(WORKSPACE, "gate")
DB_PATH = os.path.join(GATE_DIR, "cryptopluse.db")
PRICE_INDEX_JSON = os.path.join(MEMORY, "price_index.json")
PRICE_INDEX_CSV = os.path.join(MEMORY, "price_index.csv")
DIGEST_DIR = os.path.join(MEMORY, "digests")

PLANS = {
    "pilot":        {"daily_limit": 100,  "label": "Pilot (Free Trial)"},
    "starter":      {"daily_limit": 500,  "label": "Retail Starter — $59/mo"},
    "growth":       {"daily_limit": 2000, "label": "Retail Growth — $199/mo"},
    "professional": {"daily_limit": 5000, "label": "Professional — $499/mo"},
    "institutional":{"daily_limit": 99999,"label": "Institutional — $1,000/mo"},
}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            plan TEXT NOT NULL DEFAULT 'pilot',
            api_key TEXT UNIQUE NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            billing TEXT NOT NULL DEFAULT 'monthly'
        );
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_usage_key_ts ON usage_log(api_key, ts);
    """)
    db.commit()
    db.close()


def generate_api_key() -> str:
    raw = secrets.token_hex(24)
    return f"cp_{raw}"


# ---------------------------------------------------------------------------
# Auth & rate limiting
# ---------------------------------------------------------------------------

def authenticate(api_key: str | None, endpoint: str) -> dict:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing api_key parameter")
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    if not row or not row["active"]:
        db.close()
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    plan = row["plan"]
    daily_limit = PLANS.get(plan, {}).get("daily_limit", 100)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = db.execute(
        "SELECT COUNT(*) as c FROM usage_log WHERE api_key = ? AND ts >= ?",
        (api_key, today)
    ).fetchone()["c"]
    if count >= daily_limit:
        db.close()
        raise HTTPException(status_code=429, detail=f"Daily limit ({daily_limit}) exceeded for plan '{plan}'")
    db.execute(
        "INSERT INTO usage_log (api_key, endpoint, ts) VALUES (?, ?, ?)",
        (api_key, endpoint, datetime.now(timezone.utc).isoformat())
    )
    db.commit()
    result = dict(row)
    db.close()
    return result


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def read_json_file(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Data not found: {os.path.basename(path)}")


def read_text_file(path: str) -> str:
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Data not found: {os.path.basename(path)}")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CryptoPluse Data Gate",
    description="Clean, time-stamped crypto signal data — built for traders who move fast.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    os.makedirs(GATE_DIR, exist_ok=True)
    os.makedirs(DIGEST_DIR, exist_ok=True)
    init_db()


# -- Public endpoints -------------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "CryptoPluse Data Gate",
        "version": "1.0.0",
        "blurb": "Clean, time-stamped crypto signal data — built for traders who move fast.",
        "docs": "/docs",
        "signup": "/signup",
    }


@app.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


# -- Signup -----------------------------------------------------------------

@app.post("/signup")
def signup(
    name: str = Form(...),
    email: str = Form(...),
    plan: str = Form("pilot"),
    billing: str = Form("monthly"),
):
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose from: {list(PLANS.keys())}")
    if billing not in ("monthly", "annual"):
        raise HTTPException(status_code=400, detail="Billing must be 'monthly' or 'annual'")
    api_key = generate_api_key()
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, plan, api_key, active, created_at, billing) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (name, email, plan, api_key, datetime.now(timezone.utc).isoformat(), billing)
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.close()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.close()
    return {
        "status": "success",
        "message": f"Welcome to CryptoPluse, {name}!",
        "api_key": api_key,
        "plan": plan,
        "plan_label": PLANS[plan]["label"],
        "daily_limit": PLANS[plan]["daily_limit"],
        "billing": billing,
        "note": "Save your API key securely. You will need it for all data requests.",
    }


# -- Gated data endpoints --------------------------------------------------

@app.get("/api/v1/price_index.json")
def price_index_json(api_key: str = Query(None)):
    authenticate(api_key, "/api/v1/price_index.json")
    return JSONResponse(content=read_json_file(PRICE_INDEX_JSON))


@app.get("/api/v1/price_index.csv")
def price_index_csv(api_key: str = Query(None)):
    authenticate(api_key, "/api/v1/price_index.csv")
    return PlainTextResponse(content=read_text_file(PRICE_INDEX_CSV), media_type="text/csv")


@app.get("/api/v1/digests/daily.csv")
def daily_csv(api_key: str = Query(None)):
    authenticate(api_key, "/api/v1/digests/daily.csv")
    return PlainTextResponse(content=read_text_file(os.path.join(DIGEST_DIR, "daily.csv")), media_type="text/csv")


@app.get("/api/v1/digests/daily.json")
def daily_json(api_key: str = Query(None)):
    authenticate(api_key, "/api/v1/digests/daily.json")
    return JSONResponse(content=read_json_file(os.path.join(DIGEST_DIR, "daily.json")))


@app.get("/api/v1/digests/weekly.csv")
def weekly_csv(api_key: str = Query(None)):
    authenticate(api_key, "/api/v1/digests/weekly.csv")
    return PlainTextResponse(content=read_text_file(os.path.join(DIGEST_DIR, "weekly.csv")), media_type="text/csv")


@app.get("/api/v1/digests/weekly.json")
def weekly_json(api_key: str = Query(None)):
    authenticate(api_key, "/api/v1/digests/weekly.json")
    return JSONResponse(content=read_json_file(os.path.join(DIGEST_DIR, "weekly.json")))


# -- Usage stats (self-service) ---------------------------------------------

@app.get("/api/v1/usage")
def usage(api_key: str = Query(None)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing api_key")
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=403, detail="Invalid API key")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = db.execute(
        "SELECT COUNT(*) as c FROM usage_log WHERE api_key = ? AND ts >= ?",
        (api_key, today)
    ).fetchone()["c"]
    total_count = db.execute(
        "SELECT COUNT(*) as c FROM usage_log WHERE api_key = ?",
        (api_key,)
    ).fetchone()["c"]
    db.close()
    plan = row["plan"]
    return {
        "owner": row["name"],
        "plan": plan,
        "plan_label": PLANS.get(plan, {}).get("label", plan),
        "daily_limit": PLANS.get(plan, {}).get("daily_limit", 100),
        "requests_today": today_count,
        "requests_total": total_count,
        "billing": row["billing"],
        "member_since": row["created_at"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gate.main:app", host="0.0.0.0", port=8080, reload=True)
