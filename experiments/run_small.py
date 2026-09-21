#!/usr/bin/env python3
"""Two-hour theory check on short integer problems.

Probe one sample at 2048 tokens. Keep answers that finish inside the cap.
Easy band: first sample correct under 2048 tokens.
Medium band: first sample hit a 4096-token cap, and a later sample boxed the gold answer.
Then n=1,4,16 share one pool of 16. Four ratings rank proofs and do not enter A/τ.
Reflection is one critique and one revision on eight medium problems.
The i.i.d. control is sample 1 from the same pool.
"""

from __future__ import annotations

import itertools
import json
import os
import random
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from metrics import extract_answer

ROOT = Path(__file__).resolve().parent
PROBLEMS = json.loads((ROOT / "short_problems.json").read_text())
OUT = ROOT / "results" / "small"
OUT.mkdir(parents=True, exist_ok=True)

API_PORTS = list(range(8000, 8008))
_rr = itertools.count()
MODEL = "qwen3-4b"
SEED = 1234
TEMP = 1.0
TOP_P = 0.95
PROOF_MAX = int(os.environ.get("PROOF_MAX", "2048"))
VERIFY_MAX = 512
N_POOL = 16
K_RATINGS = 4
WIDTHS = (1, 4, 16)
WORKERS = 48
BAND = 12
REFLECT_N = 8


def post(payload: dict, timeout: int = 900) -> dict:
    data = json.dumps(payload).encode()
    last = None
    for attempt in range(8):
        port = API_PORTS[next(_rr) % len(API_PORTS)]
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            detail = ""
            if hasattr(exc, "read"):
                try:
                    detail = exc.read().decode()[:400]
                except Exception:
                    detail = ""
            last = RuntimeError(f"{exc} {detail}".strip())
            time.sleep(1 + attempt)
    raise RuntimeError(last)


def chat(prompt: str, max_tokens: int, seed: int) -> dict:
    t0 = time.time()
    body = post(
        {
            "model": MODEL,
            "temperature": TEMP,
            "top_p": TOP_P,
            "max_tokens": max_tokens,
            "seed": seed,
            "messages": [{"role": "user", "content": prompt}],
        }
    )
    choice = body["choices"][0]
    message = choice["message"]
    text = message.get("content") or ""
    reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
    usage = body.get("usage") or {}
    return {
        "text": text,
        "reasoning": reasoning,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "finish_reason": choice.get("finish_reason"),
        "seconds": round(time.time() - t0, 3),
    }


def extract_rating(text: str):
    matches = re.findall(r"(?<![\d.])(0\.5|1\.0|0\.0|1|0)(?![\d.])", text or "")
    if not matches:
        return None
    value = float(matches[-1])
    if value not in (0.0, 0.5, 1.0):
        return None
    return value


def solve_prompt(problem: str) -> str:
    return (
        "Solve this math problem. The answer is an integer. "
        "Put the final answer in \\boxed{}.\n\n"
        f"{problem}"
    )


def verify_prompt(problem: str, solution: str) -> str:
    return (
        "Check the solution. End with a single rating on its own line: "
        "1 if correct, 0.5 if partly correct, or 0 if incorrect.\n\n"
        f"Problem:\n{problem}\n\nSolution:\n{solution}"
    )


def critique_prompt(problem: str, solution: str) -> str:
    return (
        "Name the first serious mistake in the solution, or say that you find none. "
        "Be specific. Do not rewrite the solution.\n\n"
        f"Problem:\n{problem}\n\nSolution:\n{solution}"
    )


def revise_prompt(problem: str, solution: str, critique: str) -> str:
    return (
        "Rewrite the solution using the critique. The answer is an integer. "
        "Put it in \\boxed{}.\n\n"
        f"Problem:\n{problem}\n\nPrevious solution:\n{solution}\n\nCritique:\n{critique}"
    )


def stop_prompt(problem: str, prefix: str) -> str:
    return (
        "A solution was cut off at this prefix. "
        "Reply with STOP if the prefix already determines the correct integer answer, "
        "otherwise CONTINUE.\n\n"
        f"Problem:\n{problem}\n\nPrefix:\n{prefix}"
    )


def full_text(row: dict) -> str:
    return ((row.get("reasoning") or "") + "\n" + (row.get("text") or "")).strip()


def clip_text(text: str, limit: int = 6000) -> str:
    if len(text) <= limit:
        return text
    head = limit // 5
    return text[:head] + "\n...\n" + text[-(limit - head) :]


def finished(row: dict) -> bool:
    return row.get("answer") is not None and row.get("finish_reason") != "length"


def run_one(job: dict) -> dict:
    kind = job["kind"]
    problem = job["problem"]
    if kind == "solve":
        out = chat(solve_prompt(problem), int(job.get("max_tokens", PROOF_MAX)), job["seed"])
        out["answer"] = extract_answer(full_text(out))
    elif kind == "verify":
        out = chat(verify_prompt(problem, job["solution"]), VERIFY_MAX, job["seed"])
        out["rating"] = extract_rating(full_text(out))
    elif kind == "critique":
        out = chat(critique_prompt(problem, job["solution"]), int(job.get("max_tokens", VERIFY_MAX)), job["seed"])
    elif kind == "revise":
        out = chat(revise_prompt(problem, job["solution"], job["critique"]), int(job.get("max_tokens", PROOF_MAX)), job["seed"])
        out["answer"] = extract_answer(full_text(out))
    elif kind == "stop":
        out = chat(stop_prompt(problem, job["prefix"]), 256, job["seed"])
        blob = full_text(out).upper()
        out["decision"] = "STOP" if "STOP" in blob and "CONTINUE" not in blob else "CONTINUE"
    else:
        raise ValueError(kind)
    out["kind"] = kind
    out["meta"] = {k: v for k, v in job.items() if k not in {"problem", "solution", "critique", "prefix"}}
    return out


def pool_map(jobs: list[dict]) -> list[dict]:
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(run_one, job) for job in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            results.append(fut.result())
            if i % 8 == 0 or i == len(jobs):
                print(f"  finished {i}/{len(jobs)}", flush=True)
    return results


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")


def tokens(row: dict) -> int:
    return int(row.get("completion_tokens") or 0) + int(row.get("prompt_tokens") or 0)


def mean(xs: list[float]):
    vals = [x for x in xs if x is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def by_idx_map():
    return {p["idx"]: p for p in PROBLEMS}


def probe() -> None:
    jobs = [
        {
            "kind": "solve",
            "problem": p["problem"],
            "idx": p["idx"],
            "sample": 0,
            "seed": SEED + p["idx"],
            "max_tokens": PROOF_MAX,
        }
        for p in PROBLEMS
    ]
    rows = pool_map(jobs)
    write_jsonl(OUT / "probe.jsonl", rows)
    gold = {p["idx"]: p["answer"] for p in PROBLEMS}
    easy, medium = [], []
    for row in rows:
        if not finished(row):
            continue
        idx = row["meta"]["idx"]
        item = {
            "idx": idx,
            "tokens": row.get("completion_tokens"),
            "answer": row.get("answer"),
            "gold": gold[idx],
            "correct": row.get("answer") == gold[idx],
        }
        (easy if item["correct"] else medium).append(item)
    easy.sort(key=lambda r: r["tokens"])
    medium.sort(key=lambda r: r["tokens"])
    report = {
        "proof_max": PROOF_MAX,
        "n_probe": len(rows),
        "finished": len(easy) + len(medium),
        "easy_available": len(easy),
        "medium_available": len(medium),
        "easy": easy[:BAND],
        "medium": medium[:BAND],
        "ready": len(easy) >= 8 and len(medium) >= 8,
    }
    (OUT / "cases.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("finished", "easy_available", "medium_available", "ready")}, indent=2))


def load_rows(name: str) -> list[dict]:
    path = OUT / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def grid() -> None:
    cases = json.loads((OUT / "cases.json").read_text())
    if not cases.get("ready"):
        raise SystemExit("bands are not ready")
    chosen = []
    for band, items in (("easy", cases["easy"]), ("medium", cases["medium"])):
        for item in items:
            problem = by_idx_map()[item["idx"]]
            chosen.append({**problem, "band": band})
    reflect_ids = [p["idx"] for p in chosen if p["band"] == "medium"][:REFLECT_N]

    print("generating pool", flush=True)
    gen_path = OUT / "generations.jsonl"
    if gen_path.exists() and gen_path.stat().st_size > 0:
        solved = load_rows("generations.jsonl")
        print(f"resume generations {len(solved)}", flush=True)
    else:
        jobs = []
        for p in chosen:
            for j in range(N_POOL):
                jobs.append(
                    {
                        "kind": "solve",
                        "problem": p["problem"],
                        "idx": p["idx"],
                        "sample": j,
                        "band": p["band"],
                        "seed": SEED + p["idx"] * 1000 + j,
                    }
                )
        solved = pool_map(jobs)
        write_jsonl(gen_path, solved)

    print("verifying", flush=True)
    ver_path = OUT / "verifications.jsonl"
    if ver_path.exists() and ver_path.stat().st_size > 0:
        verified = load_rows("verifications.jsonl")
        print(f"resume verifications {len(verified)}", flush=True)
    else:
        vjobs = []
        for row in solved:
            for k in range(K_RATINGS):
                vjobs.append(
                    {
                        "kind": "verify",
                        "problem": by_idx_map()[row["meta"]["idx"]]["problem"],
                        "solution": clip_text(full_text(row)),
                        "idx": row["meta"]["idx"],
                        "sample": row["meta"]["sample"],
                        "k": k,
                        "seed": SEED + 500000 + row["meta"]["idx"] * 100 + row["meta"]["sample"] * 10 + k,
                    }
                )
        verified = pool_map(vjobs)
        write_jsonl(ver_path, verified)

    print("reflection", flush=True)
    ref_path = OUT / "reflections.json"
    if ref_path.exists() and ref_path.stat().st_size > 0:
        reflections = json.loads(ref_path.read_text())
        print("resume reflections", flush=True)
    else:
        reflections = []
        base = {}
        for idx in reflect_ids:
            row = next(r for r in solved if r["meta"]["idx"] == idx and r["meta"]["sample"] == 0)
            base[idx] = row
        critiques = pool_map(
            [
                {
                    "kind": "critique",
                    "problem": by_idx_map()[idx]["problem"],
                    "solution": clip_text(full_text(base[idx])),
                    "idx": idx,
                    "seed": SEED + 700000 + idx,
                }
                for idx in reflect_ids
            ]
        )
        crit_by = {row["meta"]["idx"]: row for row in critiques}
        revised = pool_map(
            [
                {
                    "kind": "revise",
                    "problem": by_idx_map()[idx]["problem"],
                    "solution": clip_text(full_text(base[idx])),
                    "critique": full_text(crit_by[idx])[:3000],
                    "idx": idx,
                    "seed": SEED + 800000 + idx,
                }
                for idx in reflect_ids
            ]
        )
        rev_by = {row["meta"]["idx"]: row for row in revised}
        for idx in reflect_ids:
            reflections.append(
                {
                    "idx": idx,
                    "critique": crit_by[idx],
                    "revised": rev_by[idx],
                    "base_answer": base[idx].get("answer"),
                    "resample_answer": next(
                        r.get("answer") for r in solved if r["meta"]["idx"] == idx and r["meta"]["sample"] == 1
                    ),
                    "resample_tokens": tokens(
                        next(r for r in solved if r["meta"]["idx"] == idx and r["meta"]["sample"] == 1)
                    ),
                }
            )
        ref_path.write_text(json.dumps(reflections, ensure_ascii=False))

    print("stop checks", flush=True)
    stops = []
    for item in reflections:
        problem = by_idx_map()[item["idx"]]
        text = full_text(item["revised"])
        comp = item["revised"].get("completion_tokens") or 1
        for frac, name in ((0.25, "early"), (0.75, "late")):
            prefix = text[: max(1, int(len(text) * frac))]
            decision = run_one(
                {
                    "kind": "stop",
                    "problem": problem["problem"],
                    "prefix": prefix[:8000],
                    "idx": item["idx"],
                    "cut": name,
                    "seed": SEED + 900000 + item["idx"] * 10 + int(frac * 100),
                }
            )
            gold = problem["answer"]
            stops.append(
                {
                    "idx": item["idx"],
                    "cut": name,
                    "fraction": frac,
                    "gold_in_prefix": bool(re.search(rf"(?<!\d){gold}(?!\d)", prefix)),
                    "decision": decision["decision"],
                    "revised_tokens": comp,
                    "revised_answer": item["revised"].get("answer"),
                    "gold": gold,
                }
            )
    (OUT / "stops.json").write_text(json.dumps(stops, indent=2))
    summary = summarize(chosen, solved, verified, reflections, stops)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2)[:5000], flush=True)


def band_width(chosen, solved, verified, band: str, n: int) -> dict:
    group = [p for p in chosen if p["band"] == band]
    score = {}
    for row in verified:
        key = (row["meta"]["idx"], row["meta"].get("sample"))
        score.setdefault(key, []).append(row.get("rating"))
    correct_pass = correct_sel = correct_vote = 0
    read = 0
    for p in group:
        rows = [r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] < n]
        answers = [r.get("answer") for r in rows]
        correct_pass += int(any(a == p["answer"] for a in answers))
        votes: dict[int, int] = {}
        for a in answers:
            if a is None:
                continue
            votes[a] = votes.get(a, 0) + 1
        if votes:
            winner = max(votes, key=lambda a: (votes[a], -a))
            correct_vote += int(winner == p["answer"])
        best = None
        best_s = -1.0
        for r in rows:
            s = mean(score.get((p["idx"], r["meta"]["sample"]), []))
            if s is None:
                continue
            if s > best_s:
                best_s = s
                best = r.get("answer")
        correct_sel += int(best == p["answer"])
        read += sum(tokens(r) for r in rows)
    nprob = len(group)
    acc = correct_pass / nprob
    tau = (read / nprob) / 1024
    return {
        "band": band,
        "n": n,
        "of": nprob,
        "pass_at_n": correct_pass,
        "vote": correct_vote,
        "selected": correct_sel,
        "A_pass": round(acc, 4),
        "A_vote": round(correct_vote / nprob, 4),
        "A_selected": round(correct_sel / nprob, 4),
        "tokens_per_problem": round(read / nprob, 1),
        "tau": round(tau, 4),
        "A_pass_over_tau": None if tau == 0 else round(acc / tau, 6),
    }


def ratio(later: float, earlier: float):
    if earlier == 0:
        return None
    return round(later / earlier, 4)


def bootstrap(chosen, solved, band: str) -> dict:
    group = [p for p in chosen if p["band"] == band]
    rng = random.Random(SEED)
    stats = {n: [] for n in (1, 16)}
    for _ in range(2000):
        sample = [group[rng.randrange(len(group))] for _ in group]
        for n in (1, 16):
            hit = 0
            read = 0
            for p in sample:
                rows = [r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] < n]
                hit += int(any(r.get("answer") == p["answer"] for r in rows))
                read += sum(tokens(r) for r in rows)
            acc = hit / len(sample)
            tau = (read / len(sample)) / 1024
            stats[n].append(acc / tau if tau else 0.0)
    out = {}
    for n, vals in stats.items():
        vals.sort()
        out[str(n)] = {
            "A_pass_over_tau_p05": round(vals[int(0.05 * len(vals))], 6),
            "A_pass_over_tau_p95": round(vals[int(0.95 * len(vals))], 6),
        }
    return out


def summarize(chosen, solved, verified, reflections, stops) -> dict:
    widths = [band_width(chosen, solved, verified, band, n) for band in ("easy", "medium") for n in WIDTHS]
    bars = []
    for band in ("easy", "medium"):
        cells = {c["n"]: c for c in widths if c["band"] == band}
        bars.append(
            {
                "band": band,
                "A4_over_A1": ratio(cells[4]["A_pass"], cells[1]["A_pass"]),
                "bar_4_over_1": 4,
                "A16_over_A4": ratio(cells[16]["A_pass"], cells[4]["A_pass"]),
                "bar_16_over_4": 4,
                "pass_clears_1_to_4": (ratio(cells[4]["A_pass"], cells[1]["A_pass"]) or 0) > 4,
                "pass_clears_4_to_16": (ratio(cells[16]["A_pass"], cells[4]["A_pass"]) or 0) > 4,
            }
        )
    refl = []
    gold = {p["idx"]: p["answer"] for p in chosen}
    for item in reflections:
        g = gold[item["idx"]]
        base_tok = tokens(next(r for r in solved if r["meta"]["idx"] == item["idx"] and r["meta"]["sample"] == 0))
        refl.append(
            {
                "idx": item["idx"],
                "gold": g,
                "base_correct": item.get("base_answer") == g,
                "revised_correct": item["revised"].get("answer") == g,
                "resample_correct": item.get("resample_answer") == g,
                "revise_tokens": tokens(item["critique"]) + tokens(item["revised"]) + base_tok,
                "resample_tokens": item.get("resample_tokens"),
            }
        )
    return {
        "proof_max": PROOF_MAX,
        "alpha": 1,
        "widths": widths,
        "pass_versus_bar": bars,
        "bootstrap_A_over_tau": {band: bootstrap(chosen, solved, band) for band in ("easy", "medium")},
        "reflection": refl,
        "stops": stops,
        "null_ratings": sum(1 for v in verified if v.get("rating") is None),
        "verifications": len(verified),
    }


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "probe"
    if stage == "probe":
        probe()
    elif stage == "grid":
        grid()
    else:
        raise SystemExit("stage must be probe or grid")
