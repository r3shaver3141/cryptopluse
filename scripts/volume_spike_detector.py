#!/usr/bin/env python3
"""Volume spike detector (non-ACP).

- Fetches CoinGecko /coins/markets for configured coins
- Maintains rolling volume history (window=N) in memory/volume_history.json
- Flags a spike when latest_volume > spike_mult * avg(previous_window)
- Writes alerts to memory/volume_alerts.log (separate log as requested)
- Also writes per-coin logs to memory/<symbol>_volume_spikes.log
- Updates memory/price_index.json with latest snapshot for convenience

Designed to be run every 5 minutes via cron/launchd.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

WORKSPACE = "/Users/shaver/.openclaw/workspace"
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
SCRIPTS_DIR = os.path.join(MEMORY_DIR, "scripts")

COIN_LIST_PATH = os.path.join(MEMORY_DIR, "coin_list.json")
HISTORY_PATH = os.path.join(MEMORY_DIR, "volume_history.json")
ALERTS_LOG_PATH = os.path.join(MEMORY_DIR, "volume_alerts.log")
PRICE_INDEX_PATH = os.path.join(MEMORY_DIR, "price_index.json")

WINDOW = 5
SPIKE_MULT = 2.0
VS_CURRENCY = "usd"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def write_json(path: str, obj) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def append_line(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def fetch_markets(coin_ids: list[str]) -> list[dict]:
    ids = ",".join(coin_ids)
    url = (
        "https://api.coingecko.com/api/v3/coins/markets"
        f"?vs_currency={VS_CURRENCY}"
        f"&ids={ids}"
        "&order=market_cap_desc"
        f"&per_page={len(coin_ids)}"
        "&page=1"
    )

    req = Request(url, headers={"User-Agent": "openclaw-volume-detector/1.0"})
    with urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def main() -> int:
    ts = utc_now_iso()

    coin_list = read_json(COIN_LIST_PATH, default=[])
    if not coin_list:
        append_line(ALERTS_LOG_PATH, f"{ts} ERROR: coin_list.json missing/empty")
        return 2

    # coin_list items: {id, symbol, name}
    coin_ids = [c["id"] for c in coin_list]
    id_to_symbol = {c["id"]: c["symbol"].lower() for c in coin_list}

    try:
        markets = fetch_markets(coin_ids)
    except HTTPError as e:
        append_line(ALERTS_LOG_PATH, f"{ts} ERROR: HTTP {e.code} fetching markets")
        return 3
    except URLError as e:
        append_line(ALERTS_LOG_PATH, f"{ts} ERROR: network fetching markets: {e}")
        return 3
    except Exception as e:
        append_line(ALERTS_LOG_PATH, f"{ts} ERROR: unexpected fetching markets: {e}")
        return 3

    # Build latest snapshot (also used by other steps)
    price_index: dict = {"fetched_at": ts}

    latest_vols: dict[str, float] = {}
    for m in markets:
        cid = m.get("id")
        sym = id_to_symbol.get(cid)
        if not sym:
            continue
        vol = float(m.get("total_volume") or 0.0)
        latest_vols[sym] = vol
        price_index[sym] = {
            "price": m.get("current_price"),
            "change_24h": m.get("price_change_percentage_24h"),
            "volume": vol,
            "market_cap": m.get("market_cap"),
        }

    # Persist latest snapshot
    write_json(PRICE_INDEX_PATH, price_index)

    # Load volume history: {sym: [vol1, vol2, ...]}
    history = read_json(HISTORY_PATH, default={})
    if not isinstance(history, dict):
        history = {}

    # Ensure keys exist
    for sym in latest_vols.keys():
        if sym not in history or not isinstance(history.get(sym), list):
            history[sym] = []

    spikes_found = 0

    for sym, latest in latest_vols.items():
        prev = history.get(sym, [])
        # Compute avg of previous WINDOW samples (exclude current)
        if len(prev) >= WINDOW:
            window = prev[-WINDOW:]
            avg = sum(window) / float(WINDOW)
            if avg > 0 and latest > (SPIKE_MULT * avg):
                spikes_found += 1
                line = f"{ts} SPIKE {sym.upper()} volume={latest:.0f} avg{WINDOW}={avg:.0f} mult={latest/avg:.2f}"
                append_line(ALERTS_LOG_PATH, line)
                append_line(os.path.join(MEMORY_DIR, f"{sym}_volume_spikes.log"), line)

        # Update history (append current, keep last WINDOW)
        updated = (prev + [latest])[-WINDOW:]
        history[sym] = updated

    write_json(HISTORY_PATH, history)

    # Keep the main alerts log quiet if nothing happened.
    if spikes_found:
        append_line(ALERTS_LOG_PATH, f"{ts} INFO: spikes_found={spikes_found}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
