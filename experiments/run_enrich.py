#!/usr/bin/env python3
"""Extra checks: short generation budgets, and a critique long enough to finish."""

from __future__ import annotations

import json
from pathlib import Path

import run_small as s

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "enrich"
OUT.mkdir(parents=True, exist_ok=True)
CASES = json.loads((ROOT / "results" / "theory" / "cases.json").read_text())
PROBLEMS = {p["idx"]: p for p in json.loads((ROOT / "theory_problems.json").read_text())}
REFLECT = [212, 230, 120, 140, 122, 133, 233, 234]


def main() -> None:
    easy_jobs = []
    for item in CASES["easy"]:
        p = PROBLEMS[item["idx"]]
        for cap in (128, 256, 512, 1024):
            easy_jobs.append(
                {
                    "kind": "solve",
                    "problem": p["problem"],
                    "idx": p["idx"],
                    "sample": 0,
                    "cap": cap,
                    "seed": s.SEED + 20000 + p["idx"] * 10 + cap,
                    "max_tokens": cap,
                }
            )
    print(f"budget solves {len(easy_jobs)}", flush=True)
    budget_rows = s.pool_map(easy_jobs)
    s.write_jsonl(OUT / "budgets.jsonl", budget_rows)

    print("long critiques", flush=True)
    critiques = s.pool_map(
        [
            {
                "kind": "critique",
                "problem": PROBLEMS[idx]["problem"],
                "solution": s.clip_text(_base_text(idx)),
                "idx": idx,
                "seed": s.SEED + 30000 + idx,
                "max_tokens": 2048,
            }
            for idx in REFLECT
        ]
    )
    s.write_jsonl(OUT / "critiques.jsonl", critiques)
    crit_by = {row["meta"]["idx"]: row for row in critiques}
    print("revisions", flush=True)
    revised = s.pool_map(
        [
            {
                "kind": "revise",
                "problem": PROBLEMS[idx]["problem"],
                "solution": s.clip_text(_base_text(idx)),
                "critique": s.full_text(crit_by[idx])[:6000],
                "idx": idx,
                "seed": s.SEED + 40000 + idx,
                "max_tokens": 4096,
            }
            for idx in REFLECT
        ]
    )
    s.write_jsonl(OUT / "revisions.jsonl", revised)


def _base_text(idx: int) -> str:
    path = ROOT / "results" / "theory" / "generations.jsonl"
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["meta"]["idx"] == idx and row["meta"]["sample"] == 0:
            return s.full_text(row)
    raise KeyError(idx)


if __name__ == "__main__":
    main()
