import argparse
import requests

BASE_URL = "http://localhost:9000"


def play(user_id: str):
    print("Rock Paper Scissors Client")
    print("--------------------------")

    r = requests.post(f"{BASE_URL}/sessions", json={"user_id": user_id})
    r.raise_for_status()
    data = r.json()
    session_id = data["session_id"]
    print(f"Session started: {session_id[:8]}... (user: {user_id})")
    print()

    while True:
        move = input("Enter move (rock/paper/scissors): ")

        r = requests.post(
            f"{BASE_URL}/play",
            json={"session_id": session_id, "image": move},
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
    parser.add_argument("user_id", help="User ID for this game session")
    args = parser.parse_args()
    play(args.user_id)
