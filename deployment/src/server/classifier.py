
import random

MOVES = ["rock", "paper", "scissors"]

def inference1(input:str):
    if input in MOVES:
        return input

    return random.choice(MOVES)

def inference2(input:str):
    for move in MOVES:
        if move in input:
            return move 

    return random.choice(MOVES)

def classify_image(image_stub: str):
    '''
    Stub image classifier.
    In a real ML system:
        image -> preprocessing -> model -> predicted label
    '''
    '''
    if image_stub in MOVES:
        return image_stub

    return random.choice(MOVES)
    '''
    return inference2(image_stub)
