import os
import json
import sqlite3
import logging
import threading
from datetime import datetime, timezone

import pandas as pd
from flask import Flask, request, jsonify

from src.transforms import make_master_df, make_turns_df

DB_PATH = os.environ.get("CATAN_DB_PATH", "catan.db")
API_KEY = os.environ.get("CATAN_API_KEY")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# sqlite3 connections aren't safe to share across requests/threads; serialize writes.
_write_lock = threading.Lock()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            raw_json TEXT
        )
        """
    )
    conn.commit()


def make_game_id(game_data):
    timestamp = game_data.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    return f"colonist_game_{timestamp}"


def ingest_game_data(game_id, game_data, conn):
    """Insert one game's raw JSON + derived stats into an open connection.

    Returns False without writing anything if game_id was already ingested.
    """
    existing = conn.execute(
        "SELECT 1 FROM games WHERE game_id = ?", (game_id,)
    ).fetchone()
    if existing:
        return False

    conn.execute(
        "INSERT INTO games (game_id, raw_json) VALUES (?, ?)",
        (game_id, json.dumps(game_data))
    )

    df = pd.json_normalize(game_data)
    df["game_id"] = game_id

    master = make_master_df(df)
    turns = make_turns_df(df)

    master.to_sql('master', conn, if_exists='append', index=False)
    turns.to_sql('turns', conn, if_exists='append', index=False)

    conn.commit()
    return True


@app.post("/games")
def post_game():
    if API_KEY and request.headers.get("X-API-Key") != API_KEY:
        return jsonify(error="unauthorized"), 401

    game_data = request.get_json(silent=True)
    if not isinstance(game_data, dict):
        return jsonify(error="request body must be a JSON object"), 400

    events = game_data.get("events")
    player_summary = game_data.get("playerSummary")
    if not isinstance(events, list) or not events:
        return jsonify(error="'events' must be a non-empty list"), 400
    if not isinstance(player_summary, list) or not player_summary:
        return jsonify(error="'playerSummary' must be a non-empty list"), 400

    game_id = make_game_id(game_data)

    conn = get_connection()
    try:
        with _write_lock:
            inserted = ingest_game_data(game_id, game_data, conn)
    except Exception:
        app.logger.exception("Failed to ingest game %s", game_id)
        return jsonify(error="failed to ingest game"), 500
    finally:
        conn.close()

    if not inserted:
        return jsonify(game_id=game_id, status="duplicate"), 200

    return jsonify(game_id=game_id, status="ok"), 201


@app.get("/healthz")
def healthz():
    return jsonify(status="ok"), 200


_startup_conn = get_connection()
init_db(_startup_conn)
_startup_conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), threaded=False)
