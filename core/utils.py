import random
from typing import List, Dict

def roll_exploding_d10() -> Dict[str, object]:
    """
    Roll a d10 with exploding 10s.

    Returns:
        {
            "total": int,
            "rolls": list[int]
        }
    """
    rolls: List[int] = []

    while True:
        roll = random.randint(1, 10)
        rolls.append(roll)

        if roll != 10:
            break

    return {
        "total": sum(rolls),
        "rolls": rolls,
    }
