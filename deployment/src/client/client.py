import argparse
import getpass
import os
import random
import sys
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

DEFAULT_BASE_URL = os.environ.get("RPS_BASE_URL", "http://localhost:9000")

MOVE_CHOICES = ["rock", "paper", "scissors", "none"]


def random_image_stub() -> str:
    v = random.choice(MOVE_CHOICES)
    return "" if v == "none" else v


def play_rounds(
    auth: HTTPBasicAuth,
    base: str,
    session_id: str,
    *,
    moves: Optional[list[str]] = None,
    use_random_moves: bool = False,
    verbose: bool,
) -> Optional[dict]:
    """
    Client-side loop: one POST /play per round until match_complete.
    If moves is set, uses them in order (then random if use_random_moves and still not done).
    If use_random_moves only, picks a random stub each round.
    """
    base = base.rstrip("/")
    idx = 0
    last: Optional[dict] = None
    while True:
        if moves is not None and idx < len(moves):
            image = moves[idx]
            idx += 1
        elif use_random_moves:
            image = random_image_stub()
        else:
            break

        r = requests.post(
            f"{base}/play",
            json={"session_id": session_id, "image": image},
            auth=auth,
        )
        r.raise_for_status()
        data = r.json()
        last = data

        if verbose:
            print("\nRound:", data["round"])
            print("Player move:", data["player_move"])
            print("Server move:", data["server_move"])
            print("Round winner:", data["round_winner"])
            print("Score:", data["player_score"], "-", data["server_score"])

        if data.get("match_complete"):
            return data

    return last


def play_one_match_auto(auth: HTTPBasicAuth, base: str, username: str, verbose: bool) -> Optional[str]:
    """Create session, then random /play each round until done."""
    r = requests.post(f"{base.rstrip('/')}/sessions", json={}, auth=auth)
    r.raise_for_status()
    data = r.json()
    session_id = data["session_id"]
    max_rounds = int(data.get("max_rounds", 5))
    if verbose:
        print(f"Session started: {session_id[:8]}... (user: {username})")
        print(f"Match length: {max_rounds} rounds")
        print()

    final = play_rounds(
        auth,
        base,
        session_id,
        moves=None,
        use_random_moves=True,
        verbose=verbose,
    )
    if verbose and final:
        print("\nMATCH COMPLETE")
        print("Player Score:", final.get("player_score"))
        print("Server Score:", final.get("server_score"))
        print("Winner:", final.get("winner"))
        print()
    return final.get("winner") if final else None


def play(
    username: str,
    password: str,
    base_url: str,
    batch_moves: Optional[str],
    *,
    loops: int = 0,
) -> None:
    print("Rock Paper Scissors Client")
    print("--------------------------")

    auth = HTTPBasicAuth(username, password)
    base = base_url.rstrip("/")

    if loops > 0:
        print(f"Auto mode: {loops} game(s) with random moves (client-side loop, POST /play per round)")
        print(f"User: {username}")
        print()
        wins = {"player": 0, "server": 0, "draw": 0}
        errors = 0
        for i in range(loops):
            try:
                w = play_one_match_auto(auth, base, username, verbose=False)
                if w in wins:
                    wins[w] += 1
                if (i + 1) % 10 == 0 or i == 0:
                    print(f"  … completed {i + 1}/{loops}")
            except requests.HTTPError as e:
                errors += 1
                print(
                    f"  HTTP error game {i + 1}: {e.response.status_code} {e.response.text[:120]}",
                    file=sys.stderr,
                )
            except requests.RequestException as e:
                errors += 1
                print(f"  Request error game {i + 1}: {e}", file=sys.stderr)

        print("\nDone.")
        print(f"  Player wins: {wins['player']}")
        print(f"  Server wins: {wins['server']}")
        print(f"  Draws:       {wins['draw']}")
        print(f"  Errors:      {errors}")
        if errors:
            raise SystemExit(1)
        return

    r = requests.post(f"{base}/sessions", json={}, auth=auth)
    r.raise_for_status()
    data = r.json()
    session_id = data["session_id"]
    max_rounds = int(data.get("max_rounds", 5))
    print(f"Session started: {session_id[:8]}... (user: {username})")
    print(f"Match length: {max_rounds} rounds (one POST /play per round)")
    print()

    if batch_moves is not None:
        moves = batch_moves.split()
        if len(moves) < max_rounds:
            print(
                f"Error: need at least {max_rounds} moves, got {len(moves)}.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        moves = moves[:max_rounds]
    else:
        moves = []
        for i in range(1, max_rounds + 1):
            move = input(f"Move {i}/{max_rounds} (rock/paper/scissors): ").strip()
            moves.append(move)

    final = play_rounds(
        auth,
        base,
        session_id,
        moves=moves,
        use_random_moves=False,
        verbose=True,
    )

    if final:
        print("\nMATCH COMPLETE")
        print("Player Score:", final.get("player_score"))
        print("Server Score:", final.get("server_score"))
        print("Winner:", final.get("winner"))
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rock Paper Scissors client (POST /play once per round; simulation loops on client)",
    )
    parser.add_argument(
        "username",
        nargs="?",
        default="guest",
        help="Game username (default: guest)",
    )
    parser.add_argument(
        "password",
        nargs="?",
        default=None,
        help="Password (default: guest; prompt if omitted when username given)",
    )
    parser.add_argument(
        "--batch-moves",
        metavar="MOVES",
        help='All moves in one string, e.g. "rock paper scissors rock paper" (sent as separate /play calls)',
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=0,
        metavar="N",
        help="Run N complete games with random moves each (client-side only). Incompatible with --batch-moves.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_BASE_URL,
        help=f"Server base URL (default: {DEFAULT_BASE_URL} or RPS_BASE_URL env)",
    )
    args = parser.parse_args()

    if args.loops > 0 and args.batch_moves is not None:
        print("Error: use either --loops or --batch-moves, not both.", file=sys.stderr)
        raise SystemExit(2)

    password = args.password
    if password is None:
        if args.username == "guest":
            password = "guest"
        else:
            password = getpass.getpass(f"Password for {args.username}: ")

    play(args.username, password, args.url, args.batch_moves, loops=args.loops)
