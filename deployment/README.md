# Rock Paper Scissors -- ML Experiment (FastAPI)

This project demonstrates a simple **machine learning inference pipeline
simulation** using a Rock--Paper--Scissors game.

The goal is to mimic a real-world ML workflow where:

1.  A user provides an **image input** (stubbed as a string for now)
2.  A **classifier model** infers the user's move
3.  The **server generates a random move**
4.  The system determines the **winner of the round**
5.  After **5 rounds**, the server declares the **match winner**

The ML inference stage is currently **stubbed** and can later be
replaced with a real image classification model.

------------------------------------------------------------------------

## Project Structure

    rps_ml_match_experiment/

    requirements.txt
    README.md

    server/
        main.py          # FastAPI server
        game.py          # Game rules and random server move
        classifier.py    # Stub image classifier

    client/
        client.py        # Simple CLI client

------------------------------------------------------------------------

## Installation

Install the required dependencies:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## Running the Server

Start the FastAPI server:

``` bash
cd server
uvicorn main:app --reload
```

The server will run at:

    http://localhost:8000

Interactive API documentation is available at:

    http://localhost:8000/docs

------------------------------------------------------------------------

## Running the Client

Open another terminal and run:

``` bash
cd client
python client.py
```

You will be prompted to enter a move:

    rock
    paper
    scissors

------------------------------------------------------------------------

## Game Flow

Each round performs the following steps:

    User Input (image stub)
            ↓
    Image Classification (stub)
            ↓
    Player Move
            ↓
    Server Random Move
            ↓
    Round Winner

The match runs for **5 rounds**, after which the server determines the
winner based on the majority score.

------------------------------------------------------------------------

## Multiple Sessions

The server supports **multiple concurrent sessions**. Each game is
tracked independently:

-   **Create session:** `POST /sessions` returns a `session_id`.
-   **Play rounds:** `POST /play` with body `{ "session_id": "<id>", "image": "..." }`.
-   **Session status:** `GET /sessions/{session_id}` returns current scores,
    full round history, and match winner when complete.

Player–server engagement and the match winner are stored **per session**.

------------------------------------------------------------------------

## Example Output

    Round: 1
    Player move: rock
    Server move: scissors
    Round winner: player
    Score: 1 - 0

After five rounds:

    MATCH COMPLETE
    Player Score: 3
    Server Score: 2
    Winner: player

------------------------------------------------------------------------

## Future Improvements

Possible extensions include:

-   Replace the stub classifier with a **real image classification
    model**
-   Accept **actual image uploads** from the client
-   Persist game results for **training data collection**
-   Deploy the inference service as a **scalable ML microservice**

------------------------------------------------------------------------

## Purpose

This project is intended as a **simple demonstration of integrating an
ML inference step with a REST API service** using FastAPI.
