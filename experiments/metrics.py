"""Scoring used by the note. No network calls.

A is exact-answer accuracy of a selected answer. Tau is mean tokens read
per problem, divided by 1024. Tokens are prompt plus completion on the
solutions. The vote breaks ties toward the smaller integer.
"""

from __future__ import annotations

import random
import re
from collections import Counter


def extract_answer(text: str):
    found = re.findall(r"\\boxed\{([^{}]*)\}", text or "")
    if not found:
        found = re.findall(r"boxed\{([^{}]*)\}", text or "")
    if not found:
        return None
    nums = re.findall(r"-?\d+", found[-1].replace(",", ""))
    if not nums:
        return None
    return int(nums[-1])


def tokens_of(row: dict) -> int:
    return int(row.get("completion_tokens") or 0) + int(row.get("prompt_tokens") or 0)


def vote_winner(answers: list) -> int | None:
    votes: dict[int, int] = {}
    for answer in answers:
        if answer is None:
            continue
        votes[answer] = votes.get(answer, 0) + 1
    if not votes:
        return None
    return max(votes, key=lambda answer: (votes[answer], -answer))


def pass_hit(answers: list, gold: int) -> bool:
    return any(answer == gold for answer in answers)


def ratio_clears(later: float, earlier: float, width_later: int, width_earlier: int) -> dict:
    bar = width_later / width_earlier
    growth = None if earlier == 0 else later / earlier
    return {
        "A_ratio": None if growth is None else round(growth, 4),
        "token_bar": bar,
        "clears": bool(growth is not None and growth > bar),
    }


def bootstrap_a_over_tau(per_problem: list[tuple[int, int]], draws: int, seed: int) -> dict:
    """per_problem entries are (correct as 0/1, tokens read)."""
    rng = random.Random(seed)
    n = len(per_problem)
    scores = []
    for _ in range(draws):
        pick = [per_problem[rng.randrange(n)] for _ in range(n)]
        correct = sum(item[0] for item in pick) / n
        tau = (sum(item[1] for item in pick) / n) / 1024
        scores.append(0.0 if tau == 0 else correct / tau)
    scores.sort()
    return {
        "p05": round(scores[int(0.05 * len(scores))], 6),
        "p95": round(scores[int(0.95 * len(scores))], 6),
    }


def vote_margin(answers: list) -> tuple[int | None, int]:
    counts = Counter(answer for answer in answers if answer is not None)
    if not counts:
        return None, 0
    winner, count = max(counts.items(), key=lambda item: (item[1], -item[0]))
    return winner, count
