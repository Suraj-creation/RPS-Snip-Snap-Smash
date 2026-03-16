
import random

MOVES = ["rock", "paper", "scissors"]

def random_move():
    return random.choice(MOVES)

def decide_winner(player, server):

    if player == server:
        return "draw"

    if (
        (player == "rock" and server == "scissors") or
        (player == "paper" and server == "rock") or
        (player == "scissors" and server == "paper")
    ):
        return "player"

    return "server"
