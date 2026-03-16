import argparse
import getpass
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:9000"


def play(username: str, password: str):
    print("Rock Paper Scissors Client")
    print("--------------------------")

    auth = HTTPBasicAuth(username, password)

    r = requests.post(f"{BASE_URL}/sessions", json={}, auth=auth)
    r.raise_for_status()
    data = r.json()
    session_id = data["session_id"]
    print(f"Session started: {session_id[:8]}... (user: {username})")
    print()

    while True:
        move = input("Enter move (rock/paper/scissors): ")

        r = requests.post(
            f"{BASE_URL}/play",
            json={"session_id": session_id, "image": move},
            auth=auth,
        )
        r.raise_for_status()
        data = r.json()

        if data["match_complete"]:

            print("\nMATCH COMPLETE")
            print("Player Score:", data["player_score"])
            print("Server Score:", data["server_score"])
            print("Winner:", data["winner"])
            print()

            break

        print("\nRound:", data["round"])
        print("Player move:", data["player_move"])
        print("Server move:", data["server_move"])
        print("Round winner:", data["round_winner"])
        print("Score:", data["player_score"], "-", data["server_score"])
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rock Paper Scissors client")
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
    args = parser.parse_args()

    password = args.password
    if password is None:
        if args.username == "guest":
            password = "guest"
        else:
            password = getpass.getpass(f"Password for {args.username}: ")

    play(args.username, password)
