#!/usr/bin/env python3
"""Tier-1 theory check: 6 AIME 2025 problems, Qwen3-4B solver and verifier.

Parallel widths 1, 4, 16 share one pool of 16 samples.
Reflection runs 4 rounds from sample 0.
Resampling is the other i.i.d. samples, matched later by token count.
Verifier ratings are capped shorter than proofs so the check can finish.
"""

from __future__ import annotations

import itertools
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS = json.loads((ROOT / "aime2025.json").read_text())
SUBSET = json.loads((ROOT / "subset.json").read_text()) if (ROOT / "subset.json").exists() else [1, 6, 11, 16, 21, 26]
OUT = ROOT / "results" / "tier1"
OUT.mkdir(parents=True, exist_ok=True)

API_PORTS = list(range(8000, 8008))
_rr = itertools.count()
MODEL = "qwen3-4b"
SEED = 1234
TEMP = 1.0
TOP_P = 0.95
PROOF_MAX = int(__import__("os").environ.get("PROOF_MAX", "4096"))
VERIFY_MAX = 1024
N_POOL = 16
K_RATINGS = 4
WIDTHS = (1, 4, 16)
WORKERS = 48


def post(payload: dict, timeout: int = 600) -> dict:
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
                    detail = exc.read().decode()[:500]
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
    choice = body["choices"][0]["message"]
    text = choice.get("content") or ""
    reasoning = choice.get("reasoning_content") or choice.get("reasoning") or ""
    usage = body.get("usage") or {}
    return {
        "text": text,
        "reasoning": reasoning,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "seconds": round(time.time() - t0, 3),
    }


def extract_answer(text: str):
    blob = text or ""
    found = re.findall(r"\\boxed\{([^{}]*)\}", blob)
    if not found:
        found = re.findall(r"boxed\{([^{}]*)\}", blob)
    if not found:
        return None
    raw = found[-1].replace(",", "").strip()
    nums = re.findall(r"-?\d+", raw)
    if not nums:
        return None
    return int(nums[-1])


def extract_rating(text: str):
    blob = text or ""
    matches = re.findall(r"(?<![\d.])(0\.5|1\.0|0\.0|1|0)(?![\d.])", blob)
    if not matches:
        return None
    value = float(matches[-1])
    if value not in (0.0, 0.5, 1.0):
        return None
    return value


def solve_prompt(problem: str) -> str:
    return (
        "Solve the following AIME problem. The answer is an integer from 0 to 999. "
        "Put the final answer in \\boxed{}.\n\n"
        f"{problem}"
    )


def verify_prompt(problem: str, solution: str) -> str:
    return (
        "Check the solution to this contest problem. "
        "End your reply with a single rating on its own line: 1 if the solution is correct, "
        "0.5 if it is only partly correct, or 0 if it is incorrect.\n\n"
        f"Problem:\n{problem}\n\nSolution:\n{solution}"
    )


def critique_prompt(problem: str, solution: str) -> str:
    return (
        "Read the solution and name the first serious mistake, or say that you find none. "
        "Be specific. Do not rewrite the whole solution.\n\n"
        f"Problem:\n{problem}\n\nSolution:\n{solution}"
    )


def revise_prompt(problem: str, solution: str, critique: str) -> str:
    return (
        "Rewrite the solution using the critique. "
        "The answer is an integer from 0 to 999. Put it in \\boxed{}.\n\n"
        f"Problem:\n{problem}\n\nPrevious solution:\n{solution}\n\nCritique:\n{critique}"
    )


def stop_prompt(problem: str, prefix: str) -> str:
    return (
        "A solution was cut off at this prefix. "
        "Reply with STOP if the prefix already determines the correct integer answer, "
        "otherwise CONTINUE.\n\n"
        f"Problem:\n{problem}\n\nPrefix:\n{prefix}"
    )


def gold_in_text(text: str, answer: int) -> bool:
    return bool(re.search(rf"(?<!\d){answer}(?!\d)", text or ""))


def run_one(job: dict) -> dict:
    kind = job["kind"]
    problem = job["problem"]
    if kind == "solve":
        out = chat(solve_prompt(problem), int(job.get("max_tokens", PROOF_MAX)), job["seed"])
        out["answer"] = extract_answer((out["reasoning"] or "") + "\n" + (out["text"] or ""))
    elif kind == "verify":
        out = chat(verify_prompt(problem, job["solution"]), VERIFY_MAX, job["seed"])
        blob = (out["reasoning"] or "") + "\n" + (out["text"] or "")
        out["rating"] = extract_rating(blob)
    elif kind == "critique":
        out = chat(critique_prompt(problem, job["solution"]), VERIFY_MAX, job["seed"])
    elif kind == "revise":
        out = chat(
            revise_prompt(problem, job["solution"], job["critique"]),
            PROOF_MAX,
            job["seed"],
        )
        out["answer"] = extract_answer((out["reasoning"] or "") + "\n" + (out["text"] or ""))
    elif kind == "stop":
        out = chat(stop_prompt(problem, job["prefix"]), 512, job["seed"])
        blob = ((out["text"] or "") + "\n" + (out["reasoning"] or "")).upper()
        out["decision"] = "STOP" if "STOP" in blob and "CONTINUE" not in blob.split("STOP")[-1][:20] else (
            "STOP" if blob.strip().endswith("STOP") or "\nSTOP" in blob else "CONTINUE"
        )
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
            if i % 10 == 0 or i == len(jobs):
                print(f"  finished {i}/{len(jobs)}", flush=True)
    return results


def full_text(row: dict) -> str:
    return ((row.get("reasoning") or "") + "\n" + (row.get("text") or "")).strip()


def clip_text(text: str, limit: int = 18000) -> str:
    if len(text) <= limit:
        return text
    head = limit // 5
    return text[:head] + "\n...\n" + text[-(limit - head) :]


def mean(xs: list[float]):
    vals = [x for x in xs if x is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def tokens(row: dict) -> int:
    return int(row.get("completion_tokens") or 0) + int(row.get("prompt_tokens") or 0)


def main() -> None:
    by_idx = {p["idx"]: p for p in PROBLEMS}
    chosen = [by_idx[i] for i in SUBSET]
    t0 = time.time()

    print("generating pool", flush=True)
    gen_path = OUT / "generations.jsonl"
    ver_path = OUT / "verifications.jsonl"
    if gen_path.exists() and ver_path.exists() and gen_path.stat().st_size > 0 and ver_path.stat().st_size > 0:
        solved = [json.loads(line) for line in gen_path.read_text().splitlines() if line.strip()]
        verified = [json.loads(line) for line in ver_path.read_text().splitlines() if line.strip()]
        print(f"resuming {len(solved)} generations and {len(verified)} verifications", flush=True)
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
                        "seed": SEED + p["idx"] * 1000 + j,
                    }
                )
        solved = pool_map(jobs)
        gen_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in solved) + "\n")

        print("verifying pool", flush=True)
        vjobs = []
        for row in solved:
            solution = clip_text(full_text(row))
            for k in range(K_RATINGS):
                vjobs.append(
                    {
                        "kind": "verify",
                        "problem": by_idx[row["meta"]["idx"]]["problem"],
                        "solution": solution,
                        "idx": row["meta"]["idx"],
                        "sample": row["meta"]["sample"],
                        "k": k,
                        "seed": SEED + 500000 + row["meta"]["idx"] * 1000 + row["meta"]["sample"] * 10 + k,
                    }
                )
        verified = pool_map(vjobs)
        ver_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in verified) + "\n")

    print("reflection", flush=True)
    reflections = []
    current = {}
    for p in chosen:
        row = next(r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] == 0)
        current[p["idx"]] = full_text(row)
    for rnd in range(1, 5):
        critiques = pool_map(
            [
                {
                    "kind": "critique",
                    "problem": p["problem"],
                    "solution": clip_text(current[p["idx"]]),
                    "idx": p["idx"],
                    "round": rnd,
                    "seed": SEED + 700000 + p["idx"] * 100 + rnd,
                }
                for p in chosen
            ]
        )
        crit_by = {row["meta"]["idx"]: row for row in critiques}
        revised_rows = pool_map(
            [
                {
                    "kind": "revise",
                    "problem": p["problem"],
                    "solution": clip_text(current[p["idx"]]),
                    "critique": full_text(crit_by[p["idx"]])[:4000],
                    "idx": p["idx"],
                    "round": rnd,
                    "seed": SEED + 800000 + p["idx"] * 100 + rnd,
                }
                for p in chosen
            ]
        )
        rev_by = {row["meta"]["idx"]: row for row in revised_rows}
        rating_rows = pool_map(
            [
                {
                    "kind": "verify",
                    "problem": p["problem"],
                    "solution": clip_text(full_text(rev_by[p["idx"]])),
                    "idx": p["idx"],
                    "round": rnd,
                    "k": k,
                    "seed": SEED + 900000 + p["idx"] * 100 + rnd * 10 + k,
                }
                for p in chosen
                for k in range(K_RATINGS)
            ]
        )
        for p in chosen:
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
            current[p["idx"]] = full_text(rev_by[p["idx"]])
        print(f"  reflection round {rnd} done", flush=True)
    (OUT / "reflections.json").write_text(json.dumps(reflections, ensure_ascii=False))

    print("stop checks on round-1 reflections", flush=True)
    stops = []
    for item in reflections:
        if item["round"] != 1:
            continue
        p = by_idx[item["idx"]]
        text = full_text(item["revised"])
        # Character prefixes stand in until tokenizer counts are joined at analysis time.
        # 4096 and 8192 refer to completion tokens when the API reported them;
        # we cut the decoded text in proportion to that length.
        comp = item["revised"].get("completion_tokens") or 1
        for cap in (4096, 8192):
            if comp <= cap:
                prefix = text
            else:
                prefix = text[: int(len(text) * cap / comp)]
            decision = run_one(
                {
                    "kind": "stop",
                    "problem": p["problem"],
                    "prefix": prefix[:12000],
                    "idx": p["idx"],
                    "cap": cap,
                    "seed": SEED + 1100000 + p["idx"] * 10 + cap,
                }
            )
            stops.append(
                {
                    "idx": p["idx"],
                    "cap": cap,
                    "gold_in_prefix": gold_in_text(prefix, p["answer"]),
                    "decision": decision["decision"],
                    "completion_tokens": comp,
                }
            )
    (OUT / "stops.json").write_text(json.dumps(stops, ensure_ascii=False, indent=2))

    summary = summarize(chosen, by_idx, solved, verified, reflections, stops)
    summary["seconds"] = round(time.time() - t0, 1)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, indent=2)[:4000])
    print("elapsed_s", summary["seconds"], flush=True)


def summarize(chosen, by_idx, solved, verified, reflections, stops) -> dict:
    score = {}
    for row in verified:
        key = (row["meta"]["idx"], row["meta"].get("sample"))
        score.setdefault(key, []).append(row.get("rating"))

    widths = {}
    for n in WIDTHS:
        correct_pass = 0
        correct_sel = 0
        correct_vote = 0
        read = 0
        for p in chosen:
            rows = [r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] < n]
            rows.sort(key=lambda r: r["meta"]["sample"])
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
            read += sum(
                tokens(v)
                for v in verified
                if v["meta"]["idx"] == p["idx"] and v["meta"].get("sample", 99) < n
            )
        nprob = len(chosen)
        acc_pass = correct_pass / nprob
        tau = (read / nprob) / 1024
        widths[str(n)] = {
            "pass_at_n": correct_pass,
            "selected": correct_sel,
            "vote": correct_vote,
            "of": nprob,
            "tokens_read_per_problem": round(read / nprob, 1),
            "A_pass": acc_pass,
            "A_pass_over_tau": None if tau == 0 else round(acc_pass / tau, 6),
        }

    refl = []
    for rnd in (1, 2, 4):
        hit = 0
        read = 0
        for p in chosen:
            item = next(x for x in reflections if x["idx"] == p["idx"] and x["round"] == rnd)
            hit += int(item["revised"].get("answer") == p["answer"])
            # cumulative tokens through this round, plus the original sample
            base = next(r for r in solved if r["meta"]["idx"] == p["idx"] and r["meta"]["sample"] == 0)
            read += tokens(base)
            for r in range(1, rnd + 1):
                step = next(x for x in reflections if x["idx"] == p["idx"] and x["round"] == r)
                read += tokens(step["critique"]) + tokens(step["revised"])
                read += sum(tokens(rr) for rr in step["rating_rows"])
        nprob = len(chosen)
        acc = hit / nprob
        tau = (read / nprob) / 1024
        refl.append(
            {
                "round": rnd,
                "correct": hit,
                "of": nprob,
                "tokens_read_per_problem": round(read / nprob, 1),
                "A_over_tau": None if tau == 0 else round(acc / tau, 6),
            }
        )

    return {
        "subset": SUBSET,
        "n_ratings": K_RATINGS,
        "proof_max_tokens": PROOF_MAX,
        "widths": widths,
        "reflection": refl,
        "stops": stops,
        "null_ratings": sum(1 for v in verified if v.get("rating") is None),
        "verifications": len(verified),
    }


if __name__ == "__main__":
    main()
