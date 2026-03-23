#!/usr/bin/env python3
"""
Run many RPS games against the server in one shot.
Each match is simulated on the client: POST /sessions then POST /play once per round.

Users can be listed in simulator_config.json or loaded from the server's users_config.json
(same directory as this file's parent ../server/users_config.json).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

MOVE_CHOICES = ["rock", "paper", "scissors", "none"]


def load_users(config_path: Path) -> list[dict[str, str]]:
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        users = data.get("users")
        if isinstance(users, list) and users:
            out = []
            for u in users:
                if isinstance(u, dict) and u.get("username") and u.get("password") is not None:
                    out.append({"username": str(u["username"]), "password": str(u["password"])})
            if out:
                return out
        # Optional: merge users from users_config_path in same JSON
        ucp = data.get("users_config_path")
        if ucp:
            p = Path(ucp)
            if not p.is_absolute():
                p = config_path.parent / p
            loaded = _users_from_server_style_json(p)
            if loaded:
                return loaded

    # Default: server users_config.json next to server package
    server_users = config_path.parent.parent / "server" / "users_config.json"
    loaded = _users_from_server_style_json(server_users)
    if loaded:
        return loaded

    return [{"username": "guest", "password": "guest"}]


def _users_from_server_style_json(path: Path) -> list[dict[str, str]]:
    """Parse {\"user\": \"pass\", ...} like users_config.json."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    return [{"username": str(k), "password": str(v)} for k, v in data.items() if k and v is not None]


def random_image_stub() -> str:
    v = random.choice(MOVE_CHOICES)
    if v == "none":
        return ""
    return v


def run_game(base_url: str, auth: HTTPBasicAuth, max_rounds: int) -> dict[str, Any]:
    base = base_url.rstrip("/")
    r = requests.post(f"{base}/sessions", json={}, auth=auth, timeout=30)
    r.raise_for_status()
    data = r.json()
    session_id = data["session_id"]
    mr = int(data.get("max_rounds", max_rounds))
    last: dict[str, Any] = {}
    for _ in range(mr):
        img = random_image_stub()
        r2 = requests.post(
            f"{base}/play",
            json={"session_id": session_id, "image": img},
            auth=auth,
            timeout=30,
        )
        r2.raise_for_status()
        last = r2.json()
        if last.get("match_complete"):
            break
    return last


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate many RPS games (client-side /play loop per match)")
    parser.add_argument(
        "--games",
        type=int,
        default=100,
        help="Number of complete matches to run (default: 100)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "simulator_config.json",
        help="Path to simulator_config.json",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override base URL (default: from config or http://localhost:9000)",
    )
    args = parser.parse_args()

    cfg: dict[str, Any] = {}
    if args.config.exists():
        try:
            cfg = json.loads(args.config.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read config: {e}", file=sys.stderr)

    base_url = args.base_url or cfg.get("base_url") or "http://localhost:9000"
    users = load_users(args.config)
    default_max = int(cfg.get("default_max_rounds", 5))

    print(f"Base URL: {base_url}")
    print(f"Users pool: {len(users)} account(s)")
    print(f"Running {args.games} game(s)…")

    wins = {"player": 0, "server": 0, "draw": 0}
    errors = 0

    for i in range(args.games):
        user = random.choice(users)
        auth = HTTPBasicAuth(user["username"], user["password"])
        try:
            result = run_game(base_url, auth, default_max)
            w = result.get("winner")
            if w in wins:
                wins[w] += 1
            if (i + 1) % 10 == 0:
                print(f"  … completed {i + 1}/{args.games}")
        except requests.HTTPError as e:
            errors += 1
            print(f"  HTTP error game {i + 1}: {e.response.status_code} {e.response.text[:200]}", file=sys.stderr)
        except requests.RequestException as e:
            errors += 1
            print(f"  Request error game {i + 1}: {e}", file=sys.stderr)

    print("Done.")
    print(f"  Player wins: {wins['player']}")
    print(f"  Server wins: {wins['server']}")
    print(f"  Draws:       {wins['draw']}")
    print(f"  Errors:      {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
