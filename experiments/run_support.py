#!/usr/bin/env python3
"""Further draws on AIME problems that had no correct sample in the first eight.

Same sampler as run_aime_full.py. Seeds continue the original index, so sample
j uses seed 1234 + idx * 1000 + j for j = 8 .. 31.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import run_aime_full as full
import run_small as s

ROOT = Path(__file__).resolve().parent
PROBLEMS = {p["idx"]: p for p in json.loads((ROOT / "aime2025.json").read_text())}
OUT = ROOT / "results" / "aime_full" / "support.jsonl"
# Problems with zero correct answers in the pool of eight.
TARGETS = (13, 14, 15)
START = 8
EXTRA = 24
WORKERS = 8


def generate() -> list[dict]:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            done[(row["meta"]["idx"], row["meta"]["sample"])] = row
    jobs = []
    for idx in TARGETS:
        problem = PROBLEMS[idx]["problem"]
        for j in range(START, START + EXTRA):
            if (idx, j) in done:
                continue
            jobs.append(
                {
                    "problem": problem,
                    "idx": idx,
                    "sample": j,
                    "seed": s.SEED + idx * 1000 + j,
                }
            )
    print(f"remaining {len(jobs)} of {len(TARGETS) * EXTRA}", flush=True)
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(full.run_job, job) for job in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            with lock:
                with OUT.open("a") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            done[(row["meta"]["idx"], row["meta"]["sample"])] = row
            print(
                f"  finished {i}/{len(jobs)} idx {row['meta']['idx']} "
                f"sample {row['meta']['sample']} tokens {row.get('completion_tokens')} "
                f"answer {row.get('answer')}",
                flush=True,
            )
    return list(done.values())


if __name__ == "__main__":
    generate()
