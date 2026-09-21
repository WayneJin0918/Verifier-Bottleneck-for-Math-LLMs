#!/usr/bin/env python3
"""AIME 2025: baseline n=1 against majority vote over 16 samples.

The short-problem ablations picked this pair. Reflection lost a
token-matched comparison, and verifier selection was below the vote.
One pool of 16 serves n=1, 4, 8, and 16.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import run_small as s

ROOT = Path(__file__).resolve().parent
PROBLEMS = json.loads((ROOT / "aime2025.json").read_text())
OUT = ROOT / "results" / "aime"
OUT.mkdir(parents=True, exist_ok=True)
MAX_NEW = 10240
N_POOL = 16
WIDTHS = (1, 4, 8, 16)


def tokens(row: dict) -> int:
    return int(row.get("completion_tokens") or 0) + int(row.get("prompt_tokens") or 0)


def main() -> None:
    s.PROOF_MAX = MAX_NEW
    jobs = []
    for p in PROBLEMS:
        for j in range(N_POOL):
            jobs.append(
                {
                    "kind": "solve",
                    "problem": p["problem"],
                    "idx": p["idx"],
                    "sample": j,
                    "seed": s.SEED + p["idx"] * 1000 + j,
                    "max_tokens": MAX_NEW,
                }
            )
    print(f"aime generations {len(jobs)}", flush=True)
    rows = s.pool_map(jobs)
    s.write_jsonl(OUT / "generations.jsonl", rows)
    by = {}
    for row in rows:
        by.setdefault(row["meta"]["idx"], []).append(row)
    for rs in by.values():
        rs.sort(key=lambda r: r["meta"]["sample"])
    gold = {p["idx"]: int(p["answer"]) for p in PROBLEMS}

    def cell(n: int) -> dict:
        hit = vote = finished = 0
        read = 0
        for p in PROBLEMS:
            group = by[p["idx"]][:n]
            answers = [r.get("answer") for r in group]
            hit += int(any(a == gold[p["idx"]] for a in answers))
            votes: dict[int, int] = {}
            for a in answers:
                if a is None:
                    continue
                votes[a] = votes.get(a, 0) + 1
            if votes:
                winner = max(votes, key=lambda a: (votes[a], -a))
                vote += int(winner == gold[p["idx"]])
            finished += sum(1 for r in group if s.finished(r))
            read += sum(tokens(r) for r in group)
        nprob = len(PROBLEMS)
        acc = hit / nprob
        tau = (read / nprob) / 1024
        return {
            "n": n,
            "of": nprob,
            "pass_at_n": hit,
            "vote": vote,
            "finished_traces": finished,
            "A_pass": round(acc, 4),
            "A_vote": round(vote / nprob, 4),
            "tokens_per_problem": round(read / nprob, 1),
            "A_pass_over_tau": None if tau == 0 else round(acc / tau, 6),
            "A_vote_over_tau": None if tau == 0 else round((vote / nprob) / tau, 6),
        }

    cells = [cell(n) for n in WIDTHS]
    by_n = {c["n"]: c for c in cells}

    def clears(later: int, earlier: int) -> dict:
        a1 = by_n[earlier]["A_vote"]
        a2 = by_n[later]["A_vote"]
        bar = later / earlier
        ratio = None if a1 == 0 else round(a2 / a1, 4)
        return {
            "from": earlier,
            "to": later,
            "A_vote_ratio": ratio,
            "token_bar": bar,
            "clears": bool(ratio is not None and ratio > bar),
        }

    rng = random.Random(s.SEED)
    boot = {n: [] for n in (1, 16)}
    ids = [p["idx"] for p in PROBLEMS]
    for _ in range(2000):
        draw = [ids[rng.randrange(len(ids))] for _ in ids]
        for n in (1, 16):
            hit = 0
            read = 0
            for idx in draw:
                group = by[idx][:n]
                hit += int(any(r.get("answer") == gold[idx] for r in group))
                read += sum(tokens(r) for r in group)
            acc = hit / len(draw)
            tau = (read / len(draw)) / 1024
            boot[n].append(0.0 if tau == 0 else acc / tau)
    intervals = {}
    for n, vals in boot.items():
        vals.sort()
        intervals[str(n)] = {
            "A_pass_over_tau_p05": round(vals[int(0.05 * len(vals))], 6),
            "A_pass_over_tau_p95": round(vals[int(0.95 * len(vals))], 6),
        }

    summary = {
        "dataset": "aime2025",
        "baseline": "n=1",
        "best": "majority vote over 16 i.i.d. samples",
        "why_best": (
            "On the short-problem ablations, vote matched Pass@n and beat verifier selection. "
            "A reflection round did not beat a token-matched bundle of i.i.d. samples. "
            "Wider i.i.d. pools raised accuracy and lowered A/tau at every doubling."
        ),
        "max_new_tokens": MAX_NEW,
        "alpha": 1,
        "cells": cells,
        "vote_versus_bar": [clears(4, 1), clears(8, 4), clears(16, 8), clears(16, 1)],
        "bootstrap_A_over_tau": intervals,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
