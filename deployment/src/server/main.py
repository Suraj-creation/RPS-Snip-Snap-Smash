import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from classifier import classify_image
from game import random_move, decide_winner

app = FastAPI(title="Rock Paper Scissors ML Experiment")

# Per-session state: session_id -> { round_number, player_score, server_score, round_history, winner }
SessionState = dict
sessions: dict[str, SessionState] = {}

MAX_ROUNDS = 5


class PlayRequest(BaseModel):
    session_id: str
    image: str


class SessionResponse(BaseModel):
    session_id: str


class RoundResult(BaseModel):
    round: int
    player_move: str
    server_move: str
    round_winner: str
    player_score: int
    server_score: int


class SessionStatus(BaseModel):
    session_id: str
    round_number: int
    player_score: int
    server_score: int
    round_history: list[RoundResult]
    match_complete: bool
    winner: Optional[str] = None


def _get_session(session_id: str) -> SessionState:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


@app.post("/sessions", response_model=SessionResponse)
def create_session():
    """Create a new game session. Use the returned session_id for /play."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "round_number": 0,
        "player_score": 0,
        "server_score": 0,
        "round_history": [],
        "winner": None,
    }
    return SessionResponse(session_id=session_id)


@app.get("/sessions/{session_id}", response_model=SessionStatus)
def get_session(session_id: str):
    """Get current status and full history for a session."""
    state = _get_session(session_id)
    return SessionStatus(
        session_id=session_id,
        round_number=state["round_number"],
        player_score=state["player_score"],
        server_score=state["server_score"],
        round_history=state["round_history"],
        match_complete=state["round_number"] >= MAX_ROUNDS,
        winner=state["winner"],
    )


@app.post("/play")
def play(req: PlayRequest):
    """Play one round in the given session. After 5 rounds, match is complete and winner is set."""
    state = _get_session(req.session_id)

    if state["round_number"] >= MAX_ROUNDS:
        raise HTTPException(
            status_code=400,
            detail="Match already complete. Create a new session to play again.",
        )

    player_move = classify_image(req.image)
    server_move = random_move()
    round_winner = decide_winner(player_move, server_move)

    if round_winner == "player":
        state["player_score"] += 1
    elif round_winner == "server":
        state["server_score"] += 1

    state["round_number"] += 1
    round_result = RoundResult(
        round=state["round_number"],
        player_move=player_move,
        server_move=server_move,
        round_winner=round_winner,
        player_score=state["player_score"],
        server_score=state["server_score"],
    )
    state["round_history"].append(round_result.model_dump())

    if state["round_number"] >= MAX_ROUNDS:
        if state["player_score"] > state["server_score"]:
            state["winner"] = "player"
        elif state["server_score"] > state["player_score"]:
            state["winner"] = "server"
        else:
            state["winner"] = "draw"

        return {
            "match_complete": True,
            "round": state["round_number"],
            "player_move": player_move,
            "server_move": server_move,
            "round_winner": round_winner,
            "player_score": state["player_score"],
            "server_score": state["server_score"],
            "winner": state["winner"],
        }

    return {
        "match_complete": False,
        "round": state["round_number"],
        "player_move": player_move,
        "server_move": server_move,
        "round_winner": round_winner,
        "player_score": state["player_score"],
        "server_score": state["server_score"],
    }
