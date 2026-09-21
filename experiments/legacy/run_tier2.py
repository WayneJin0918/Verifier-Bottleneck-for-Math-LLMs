#!/usr/bin/env python3
"""Final 30-problem comparison, reusing the six-problem tier-1 runs.

Reports n=1 against n=16, and r=4 reflection against an i.i.d. resample
matched on tokens read. alpha is 1. beta and rho are not relabeled here.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import run_tier1 as t1

ROOT = t1.ROOT
TIER1 = ROOT / "results" / "tier1"
OUT = ROOT / "results" / "tier2"
OUT.mkdir(parents=True, exist_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def widths_for(problems, solved, verified) -> dict:
    score = {}
    for row in verified:
        key = (row["meta"]["idx"], row["meta"].get("sample"))
        score.setdefault(key, []).append(row.get("rating"))
    out = {}
    nprob = len(problems)
    for n in (1, 16):
        correct_pass = correct_sel = correct_vote = 0
        read = 0
        per = []
        for p in problems:
            rows = [r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] < n]
            answers = [r.get("answer") for r in rows]
            passed = int(any(a == p["answer"] for a in answers))
            correct_pass += passed
            votes: dict[int, int] = {}
            for a in answers:
                if a is not None:
                    votes[a] = votes.get(a, 0) + 1
            voted = None
            if votes:
                voted = max(votes, key=lambda a: (votes[a], -a))
                correct_vote += int(voted == p["answer"])
            best = None
            best_s = -1.0
            for r in rows:
                s = t1.mean(score.get((p["idx"], r["meta"]["sample"]), []))
                if s is not None and s > best_s:
                    best_s = s
                    best = r.get("answer")
            selected = int(best == p["answer"])
            correct_sel += selected
            tok = sum(t1.tokens(r) for r in rows)
            tok += sum(
                t1.tokens(v)
                for v in verified
                if v["meta"]["idx"] == p["idx"] and v["meta"].get("sample", 99) < n
            )
            read += tok
            per.append({"idx": p["idx"], "pass": passed, "selected": selected, "vote": int(voted == p["answer"]) if voted is not None else 0, "tokens": tok})
        acc = correct_sel / nprob
        tau = (read / nprob) / 1024
        out[str(n)] = {
            "pass_at_n": correct_pass,
            "selected": correct_sel,
            "vote": correct_vote,
            "of": nprob,
            "tokens_read_per_problem": round(read / nprob, 1),
            "A_selected": round(acc, 4),
            "A_selected_over_tau": None if tau == 0 else round(acc / tau, 6),
            "per_problem": per,
        }
    return out


def bootstrap(flags: list[int], reps: int = 2000) -> dict:
    n = len(flags)
    rng = random.Random(1234)
    means = []
    for _ in range(reps):
        means.append(sum(flags[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return {
        "mean": round(sum(flags) / n, 4),
        "lo": round(means[int(0.025 * reps)], 4),
        "hi": round(means[int(0.975 * reps)], 4),
    }


def main() -> None:
    t0 = time.time()
    by_idx = {p["idx"]: p for p in t1.PROBLEMS}
    problems = list(t1.PROBLEMS)
    subset = set(t1.SUBSET)

    solved = load_jsonl(TIER1 / "generations.jsonl")
    solved = [r for r in solved if r["meta"]["idx"] in subset]
    verified = load_jsonl(TIER1 / "verifications.jsonl")
    verified = [r for r in verified if r["meta"]["idx"] in subset and "sample" in r["meta"]]

    missing = [p for p in problems if p["idx"] not in subset]
    print(f"generating {len(missing)} remaining problems", flush=True)
    jobs = []
    for p in missing:
        for j in range(t1.N_POOL):
            jobs.append(
                {
                    "kind": "solve",
                    "problem": p["problem"],
                    "idx": p["idx"],
                    "sample": j,
                    "seed": t1.SEED + p["idx"] * 1000 + j,
                }
            )
    new_solved = t1.pool_map(jobs) if jobs else []
    solved.extend(new_solved)
    (OUT / "generations.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in solved) + "\n"
    )

    print("verifying remaining proofs", flush=True)
    vjobs = []
    for row in new_solved:
        for k in range(t1.K_RATINGS):
            vjobs.append(
                {
                    "kind": "verify",
                    "problem": by_idx[row["meta"]["idx"]]["problem"],
                    "solution": t1.clip_text(t1.full_text(row)),
                    "idx": row["meta"]["idx"],
                    "sample": row["meta"]["sample"],
                    "k": k,
                    "seed": t1.SEED + 500000 + row["meta"]["idx"] * 1000 + row["meta"]["sample"] * 10 + k,
                }
            )
    new_verified = t1.pool_map(vjobs) if vjobs else []
    verified.extend(new_verified)
    (OUT / "verifications.jsonl").write_text(
        "\n".join(json.dumps({k: v for k, v in r.items() if k != "reasoning"}, ensure_ascii=False) for r in verified) + "\n"
    )

    prior = []
    prior_path = TIER1 / "reflections.json"
    if prior_path.exists():
        prior = json.loads(prior_path.read_text())
    have = {(x["idx"], x["round"]) for x in prior}
    reflections = list(prior)
    current = {}
    for p in problems:
        row = next(r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] == 0)
        current[p["idx"]] = t1.full_text(row)
    for rnd in range(1, 5):
        todo = [p for p in problems if (p["idx"], rnd) not in have]
        if not todo:
            for p in problems:
                if (p["idx"], rnd) in have:
                    item = next(x for x in reflections if x["idx"] == p["idx"] and x["round"] == rnd)
                    current[p["idx"]] = t1.full_text(item["revised"])
            continue
        print(f"reflection round {rnd} on {len(todo)} problems", flush=True)
        critiques = t1.pool_map(
            [
                {
                    "kind": "critique",
                    "problem": p["problem"],
                    "solution": t1.clip_text(current[p["idx"]]),
                    "idx": p["idx"],
                    "round": rnd,
                    "seed": t1.SEED + 700000 + p["idx"] * 100 + rnd,
                }
                for p in todo
            ]
        )
        crit_by = {row["meta"]["idx"]: row for row in critiques}
        revised_rows = t1.pool_map(
            [
                {
                    "kind": "revise",
                    "problem": p["problem"],
                    "solution": t1.clip_text(current[p["idx"]]),
                    "critique": t1.clip_text(t1.full_text(crit_by[p["idx"]]), 4000),
                    "idx": p["idx"],
                    "round": rnd,
                    "seed": t1.SEED + 800000 + p["idx"] * 100 + rnd,
                }
                for p in todo
            ]
        )
        rev_by = {row["meta"]["idx"]: row for row in revised_rows}
        rating_rows = t1.pool_map(
            [
                {
                    "kind": "verify",
                    "problem": p["problem"],
                    "solution": t1.clip_text(t1.full_text(rev_by[p["idx"]])),
                    "idx": p["idx"],
                    "round": rnd,
                    "k": k,
                    "seed": t1.SEED + 900000 + p["idx"] * 100 + rnd * 10 + k,
                }
                for p in todo
                for k in range(t1.K_RATINGS)
            ]
        )
        for p in todo:
            mine = [r for r in rating_rows if r["meta"]["idx"] == p["idx"]]
            reflections.append(
                {
                    "idx": p["idx"],
                    "round": rnd,
                    "critique": crit_by[p["idx"]],
                    "revised": rev_by[p["idx"]],
                    "ratings": [r.get("rating") for r in mine],
                    "rating_rows": mine,
                }
            )
        for p in problems:
            item = next(x for x in reflections if x["idx"] == p["idx"] and x["round"] == rnd)
            current[p["idx"]] = t1.full_text(item["revised"])

    (OUT / "reflections.json").write_text(json.dumps(reflections, ensure_ascii=False))

    width = widths_for(problems, solved, verified)
    refl_flags = []
    re_flags = []
    refl_tokens = []
    re_tokens = []
    for p in problems:
        item = next(x for x in reflections if x["idx"] == p["idx"] and x["round"] == 4)
        refl_flags.append(int(item["revised"].get("answer") == p["answer"]))
        base = next(r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] == 0)
        tok = t1.tokens(base)
        for rnd in range(1, 5):
            step = next(x for x in reflections if x["idx"] == p["idx"] and x["round"] == rnd)
            tok += t1.tokens(step["critique"]) + t1.tokens(step["revised"])
            tok += sum(t1.tokens(rr) for rr in step["rating_rows"])
        refl_tokens.append(tok)
        cum = 0
        chosen = None
        chosen_tok = 0
        for j in range(1, t1.N_POOL):
            row = next(r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] == j)
            cum += t1.tokens(row)
            chosen = row
            chosen_tok = cum
            if cum >= tok:
                break
        re_flags.append(int(chosen is not None and chosen.get("answer") == p["answer"]))
        re_tokens.append(chosen_tok)

    nprob = len(problems)
    summary = {
        "n_problems": nprob,
        "proof_max_tokens": t1.PROOF_MAX,
        "n_ratings": t1.K_RATINGS,
        "widths": {k: {kk: vv for kk, vv in val.items() if kk != "per_problem"} for k, val in width.items()},
        "reflection_r4": {
            "correct": sum(refl_flags),
            "tokens_read_per_problem": round(sum(refl_tokens) / nprob, 1),
            "A": round(sum(refl_flags) / nprob, 4),
            "bootstrap": bootstrap(refl_flags),
        },
        "resample_matched": {
            "correct": sum(re_flags),
            "tokens_read_per_problem": round(sum(re_tokens) / nprob, 1),
            "A": round(sum(re_flags) / nprob, 4),
            "bootstrap": bootstrap(re_flags),
        },
        "selected_bootstrap": {
            "n1": bootstrap([row["selected"] for row in width["1"]["per_problem"]]),
            "n16": bootstrap([row["selected"] for row in width["16"]["per_problem"]]),
        },
        "seconds": round(time.time() - t0, 1),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
