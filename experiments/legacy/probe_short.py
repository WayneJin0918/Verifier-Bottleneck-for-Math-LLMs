#!/usr/bin/env python3
"""One sample per AIME 2025 problem. Keep problems that box an answer within the cap."""

from __future__ import annotations

import json
from pathlib import Path

import run_tier1 as t1

CAP = 11000
OUT = t1.ROOT / "probe.jsonl"


def main() -> None:
    jobs = []
    for p in t1.PROBLEMS:
        jobs.append(
            {
                "kind": "solve",
                "problem": p["problem"],
                "idx": p["idx"],
                "sample": 0,
                "seed": t1.SEED + p["idx"],
                "max_tokens": CAP,
            }
        )
    rows = t1.pool_map(jobs)
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    finished = []
    for r in rows:
        tok = r.get("completion_tokens") or 0
        if r.get("answer") is not None and tok < CAP:
            finished.append((tok, r["meta"]["idx"], r.get("answer")))
    finished.sort()
    print("finished_under_cap", len(finished))
    for tok, idx, ans in finished:
        print(f"  problem {idx} tokens {tok} answer {ans}")
    chosen = [idx for _, idx, _ in finished[:6]]
    (t1.ROOT / "subset.json").write_text(json.dumps(chosen))
    print("subset", chosen)


if __name__ == "__main__":
    main()
