#!/usr/bin/env python3
"""AIME 2025 at the model card length: one sample against a vote of 8.

Sampling follows the Qwen3-4B-Thinking-2507 card for contest problems:
temperature 0.6, top-p 0.95, top-k 20, 81920 new tokens.
The published AIME25 figure for this checkpoint is 81.3.
"""

from __future__ import annotations

import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import metrics
import run_small as s

ROOT = Path(__file__).resolve().parent
PROBLEMS = json.loads((ROOT / "aime2025.json").read_text())
OUT = ROOT / "results" / "aime_full"
OUT.mkdir(parents=True, exist_ok=True)
MAX_NEW = 81920
N_POOL = 8
WIDTHS = (1, 4, 8)
TEMP = 0.6
TOP_K = 20
PUBLISHED = 81.3


def solve_prompt(problem: str) -> str:
    return (
        "Please reason step by step, and put your final answer within \\boxed{}.\n\n"
        f"{problem}"
    )


def chat(prompt: str, seed: int) -> dict:
    t0 = __import__("time").time()
    body = s.post(
        {
            "model": s.MODEL,
            "temperature": TEMP,
            "top_p": s.TOP_P,
            "top_k": TOP_K,
            "max_tokens": MAX_NEW,
            "seed": seed,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=7200,
    )
    choice = body["choices"][0]
    message = choice["message"]
    usage = body.get("usage") or {}
    return {
        "text": message.get("content") or "",
        "reasoning": message.get("reasoning_content") or message.get("reasoning") or "",
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "finish_reason": choice.get("finish_reason"),
        "seconds": round(__import__("time").time() - t0, 3),
    }


def run_job(job: dict) -> dict:
    out = chat(solve_prompt(job["problem"]), job["seed"])
    out["answer"] = s.extract_answer((out["reasoning"] or "") + "\n" + (out["text"] or ""))
    out["kind"] = "solve"
    out["meta"] = {k: v for k, v in job.items() if k != "problem"}
    return out


def generate() -> list[dict]:
    path = OUT / "generations.jsonl"
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            done[(row["meta"]["idx"], row["meta"]["sample"])] = row
    jobs = []
    for p in PROBLEMS:
        for j in range(N_POOL):
            if (p["idx"], j) in done:
                continue
            jobs.append(
                {
                    "problem": p["problem"],
                    "idx": p["idx"],
                    "sample": j,
                    "seed": s.SEED + p["idx"] * 1000 + j,
                }
            )
    print(f"remaining {len(jobs)} of {len(PROBLEMS) * N_POOL}", flush=True)
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = [pool.submit(run_job, job) for job in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            row = fut.result()
            with lock:
                with path.open("a") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            done[(row["meta"]["idx"], row["meta"]["sample"])] = row
            if i % 4 == 0 or i == len(jobs):
                print(
                    f"  finished {i}/{len(jobs)} last idx {row['meta']['idx']} "
                    f"sample {row['meta']['sample']} tokens {row.get('completion_tokens')} "
                    f"answer {row.get('answer')}",
                    flush=True,
                )
    return list(done.values())


def summarize(rows: list[dict]) -> dict:
    by = {}
    for row in rows:
        by.setdefault(row["meta"]["idx"], []).append(row)
    for group in by.values():
        group.sort(key=lambda r: r["meta"]["sample"])
    gold = {p["idx"]: int(p["answer"]) for p in PROBLEMS}

    def cell(n: int) -> dict:
        hit = vote = stopped = 0
        read = 0
        for p in PROBLEMS:
            group = by[p["idx"]][:n]
            answers = [r.get("answer") for r in group]
            hit += int(any(a == gold[p["idx"]] for a in answers))
            winner = metrics.vote_winner(answers)
            vote += int(winner == gold[p["idx"]])
            stopped += sum(1 for r in group if r.get("finish_reason") == "stop")
            read += sum(metrics.tokens_of(r) for r in group)
        nprob = len(PROBLEMS)
        acc = vote / nprob
        tau = (read / nprob) / 1024
        return {
            "n": n,
            "of": nprob,
            "pass_at_n": hit,
            "vote": vote,
            "stopped_traces": stopped,
            "A_pass": round(hit / nprob, 4),
            "A_vote": round(acc, 4),
            "A_vote_percent": round(100 * acc, 1),
            "tokens_per_problem": round(read / nprob, 1),
            "A_vote_over_tau": None if tau == 0 else round(acc / tau, 6),
        }

    cells = [cell(n) for n in WIDTHS]
    by_n = {c["n"]: c for c in cells}

    def clears(later: int, earlier: int) -> dict:
        a1 = by_n[earlier]["A_vote"]
        a2 = by_n[later]["A_vote"]
        bar = later / earlier
        ratio = None if a1 == 0 else round(a2 / a1, 4)
        return {"from": earlier, "to": later, "A_vote_ratio": ratio, "token_bar": bar, "clears": bool(ratio is not None and ratio > bar)}

    rng = random.Random(s.SEED)
    ids = [p["idx"] for p in PROBLEMS]
    boot = []
    for _ in range(2000):
        draw = [ids[rng.randrange(len(ids))] for _ in ids]
        hit = 0
        read = 0
        for idx in draw:
            group = by[idx][:1]
            hit += int(any(r.get("answer") == gold[idx] for r in group))
            read += sum(metrics.tokens_of(r) for r in group)
        acc = hit / len(draw)
        tau = (read / len(draw)) / 1024
        boot.append(0.0 if tau == 0 else acc / tau)
    boot.sort()
    summary = {
        "dataset": "aime2025",
        "published_aime25": PUBLISHED,
        "sampling": {"temperature": TEMP, "top_p": s.TOP_P, "top_k": TOP_K, "max_new_tokens": MAX_NEW, "seed": s.SEED},
        "baseline": "n=1",
        "comparison": "majority vote over 8 i.i.d. samples",
        "cells": cells,
        "vote_versus_bar": [clears(4, 1), clears(8, 4), clears(8, 1)],
        "bootstrap_n1_A_over_tau": {
            "p05": round(boot[int(0.05 * len(boot))], 6),
            "p95": round(boot[int(0.95 * len(boot))], 6),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> None:
    rows = generate()
    summarize(rows)


if __name__ == "__main__":
    main()
