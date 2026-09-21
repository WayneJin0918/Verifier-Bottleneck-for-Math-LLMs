#!/usr/bin/env python3
"""Recompute the AIME numbers cited in the note.

Reads experiments/results/aime_full/generations.jsonl. If support.jsonl is
present, also scores the extra draws on problems 13, 14, and 15.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import metrics

ROOT = Path(__file__).resolve().parent
PROBLEMS = json.loads((ROOT / "aime2025.json").read_text())
GOLD = {p["idx"]: int(p["answer"]) for p in PROBLEMS}
GEN = ROOT / "results" / "aime_full" / "generations.jsonl"
SUPPORT = ROOT / "results" / "aime_full" / "support.jsonl"
OUT = ROOT / "results" / "aime_full" / "analysis.json"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def group_rows(rows: list[dict]) -> dict[int, list[dict]]:
    by = defaultdict(list)
    for row in rows:
        by[row["meta"]["idx"]].append(row)
    for group in by.values():
        group.sort(key=lambda row: row["meta"]["sample"])
    return by


def cell(by: dict, n: int) -> dict:
    hit = vote = read = 0
    for problem in PROBLEMS:
        group = by[problem["idx"]][:n]
        answers = [row.get("answer") for row in group]
        gold = GOLD[problem["idx"]]
        hit += int(metrics.pass_hit(answers, gold))
        winner = metrics.vote_winner(answers)
        vote += int(winner == gold)
        read += sum(metrics.tokens_of(row) for row in group)
    nprob = len(PROBLEMS)
    acc = vote / nprob
    tau = (read / nprob) / 1024
    return {
        "n": n,
        "pass_at_n": hit,
        "vote": vote,
        "A_vote": round(acc, 4),
        "tokens_per_problem": round(read / nprob, 1),
        "A_over_tau": round(acc / tau, 6),
    }


def prefix_table(by: dict) -> list[dict]:
    rows = [cell(by, n) for n in range(1, 9)]
    base = rows[0]["A_vote"]
    for row in rows:
        row["A_ratio_vs_n1"] = round(row["A_vote"] / base, 4)
        row["token_bar"] = row["n"]
        row["clears"] = row["A_ratio_vs_n1"] > row["n"]
    return rows


def single_sample_counts(by: dict) -> list[int]:
    counts = []
    for sample in range(8):
        hit = 0
        for problem in PROBLEMS:
            row = by[problem["idx"]][sample]
            hit += int(row.get("answer") == GOLD[problem["idx"]])
        counts.append(hit)
    return counts


def log_change(first: dict, last: dict) -> dict:
    d_a = math.log(last["A_vote"] / first["A_vote"])
    d_t = math.log(last["tokens_per_problem"] / first["tokens_per_problem"])
    return {
        "delta_log_A": round(d_a, 4),
        "delta_log_tau": round(d_t, 4),
        "delta_log_A_over_tau": round(d_a - d_t, 4),
        "token_ratio": round(last["tokens_per_problem"] / first["tokens_per_problem"], 3),
        "accuracy_ceiling_ratio": round(1 / first["A_vote"], 4),
    }


def problem_rows(by: dict) -> list[dict]:
    out = []
    for problem in PROBLEMS:
        idx = problem["idx"]
        group = by[idx]
        answers = [row.get("answer") for row in group[:8]]
        gold = GOLD[idx]
        counts = Counter(answer for answer in answers if answer is not None)
        winner, margin = metrics.vote_margin(answers)
        correct = sum(answer == gold for answer in answers)
        mean_tokens = sum(metrics.tokens_of(row) for row in group[:8]) / 8
        out.append(
            {
                "idx": idx,
                "gold": gold,
                "n1": answers[0],
                "vote": winner,
                "correct_in_8": correct,
                "margin": margin,
                "mean_tokens": round(mean_tokens, 1),
                "counts": {str(key): value for key, value in counts.items()},
            }
        )
    return out


def length_split(rows: list[dict]) -> dict:
    correct, wrong = [], []
    for row in rows:
        gold = GOLD[row["meta"]["idx"]]
        bucket = correct if row.get("answer") == gold else wrong
        bucket.append(metrics.tokens_of(row))
    return {
        "correct_traces": len(correct),
        "correct_mean_tokens": round(sum(correct) / len(correct), 1),
        "wrong_traces": len(wrong),
        "wrong_mean_tokens": round(sum(wrong) / len(wrong), 1),
        "wrong_over_correct": round((sum(wrong) / len(wrong)) / (sum(correct) / len(correct)), 3),
    }


def support_summary(by: dict, extra: list[dict]) -> dict | None:
    if not extra:
        return None
    added = group_rows(extra)
    out = []
    for idx in (13, 14, 15):
        answers = [row.get("answer") for row in added.get(idx, [])]
        gold = GOLD[idx]
        hits = [row["meta"]["sample"] for row in added.get(idx, []) if row.get("answer") == gold]
        counts = Counter(answer for answer in answers if answer is not None)
        base_answers = [row.get("answer") for row in by[idx][:8]]
        combined = Counter(answer for answer in base_answers + answers if answer is not None)
        mode, mode_count = combined.most_common(1)[0]
        base = sum(answer == gold for answer in base_answers)
        out.append(
            {
                "idx": idx,
                "gold": gold,
                "extra_traces": len(answers),
                "extra_correct": len(hits),
                "correct_in_32": base + len(hits),
                "extra_missing_answer": sum(answer is None for answer in answers),
                "combined_missing_answer": sum(answer is None for answer in base_answers + answers),
                "mode": mode,
                "mode_count_in_32": mode_count,
                "first_extra_hit": min(hits) if hits else None,
                "counts": {str(key): value for key, value in counts.most_common(6)},
            }
        )
    return {"problems": out}


def bootstrap_pair(by: dict) -> dict:
    def items(n: int):
        packed = []
        for problem in PROBLEMS:
            group = by[problem["idx"]][:n]
            answers = [row.get("answer") for row in group]
            winner = metrics.vote_winner(answers)
            packed.append((int(winner == GOLD[problem["idx"]]), sum(metrics.tokens_of(row) for row in group)))
        return packed

    return {
        "n1": metrics.bootstrap_a_over_tau(items(1), 2000, 1234),
        "n8": metrics.bootstrap_a_over_tau(items(8), 2000, 1234),
    }


def gold_box_fraction(row: dict, gold: int):
    """Start and tail of the last boxed integer, as fractions of the trace."""
    text = (row.get("reasoning") or "") + "\n" + (row.get("text") or "")
    if row.get("answer") != gold or not text:
        return None
    found = list(re.finditer(r"\\boxed\{([^{}]*)\}", text))
    if not found:
        return None
    match = found[-1]
    nums = re.findall(r"-?\d+", match.group(1).replace(",", ""))
    if not nums or int(nums[-1]) != gold:
        return None
    return match.start() / len(text), (len(text) - match.end()) / len(text)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[int(q * (len(ordered) - 1))]


def box_summary(rows: list[dict], gold_of) -> dict:
    pairs = []
    for row in rows:
        pair = gold_box_fraction(row, gold_of(row))
        if pair is not None:
            pairs.append(pair)
    starts = [pair[0] for pair in pairs]
    tails = [pair[1] for pair in pairs]
    return {
        "traces": len(rows),
        "correct_boxes": len(pairs),
        "start_p50": round(percentile(starts, 0.5), 4),
        "start_min": round(min(starts), 4),
        "tail_p50": round(percentile(tails, 0.5), 4),
        "tail_p90": round(percentile(tails, 0.9), 4),
        "boxes_by_start_quartile": {
            "0.25": sum(start <= 0.25 for start in starts),
            "0.50": sum(start <= 0.50 for start in starts),
            "0.75": sum(start <= 0.75 for start in starts),
        },
    }


def theory_boxes() -> dict:
    theory = json.loads((ROOT / "theory_problems.json").read_text())
    gold = {item["idx"]: int(item["answer"]) for item in theory}
    rows = load_jsonl(ROOT / "results" / "theory" / "generations.jsonl")
    out = {}
    for band in ("easy", "medium"):
        band_rows = [row for row in rows if row["meta"].get("band") == band]
        out[band] = box_summary(band_rows, lambda row, gold=gold: gold[row["meta"]["idx"]])
    path = ROOT / "results" / "theory" / "box.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    easy, medium = out["easy"], out["medium"]
    assert easy["correct_boxes"] == 192 and easy["boxes_by_start_quartile"]["0.75"] == 0
    assert medium["traces"] == 192 and medium["correct_boxes"] == 85
    assert medium["boxes_by_start_quartile"]["0.75"] == 0
    assert medium["start_min"] > 0.85
    return out


def aime_splits(problems: list[dict]) -> dict:
    n1_wrong = [row["idx"] for row in problems if row["n1"] != row["gold"]]
    never = [row["idx"] for row in problems if row["correct_in_8"] == 0]
    partial = [row["idx"] for row in problems if 0 < row["correct_in_8"] < 8]
    assert n1_wrong == [10, 13, 14, 15, 30]
    assert never == [13, 14, 15]
    assert partial == [7, 10, 20, 30]
    return {"wrong_at_n1": n1_wrong, "never_correct_in_8": never, "correct_but_not_unanimous": partial}


def main() -> None:
    rows = load_jsonl(GEN)
    if len(rows) != 240:
        raise SystemExit(f"expected 240 generations, found {len(rows)}")
    by = group_rows(rows)
    table = prefix_table(by)
    singles = single_sample_counts(by)
    change = log_change(table[0], table[7])
    analysis = {
        "protocol": {
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "max_new_tokens": 81920,
            "seed": 1234,
            "pool": 8,
        },
        "published_aime25": 81.3,
        "prefix": table,
        "single_sample_correct": singles,
        "single_sample_mean": round(sum(singles) / len(singles), 2),
        "log_change_n1_to_n8": change,
        "A_over_tau_ratio_n8_over_n1": round(table[7]["A_over_tau"] / table[0]["A_over_tau"], 3),
        "length": length_split(rows),
        "problems": problem_rows(by),
        "bootstrap_A_over_tau": bootstrap_pair(by),
        "all_stopped": all(row.get("finish_reason") == "stop" for row in rows),
        "max_completion_tokens": max(row["completion_tokens"] for row in rows),
        "support": support_summary(by, load_jsonl(SUPPORT)),
        "splits": aime_splits(problem_rows(by)),
        "box": box_summary(rows, lambda row: GOLD[row["meta"]["idx"]]),
        "theory_box": theory_boxes(),
    }
    # The note's headline cells.
    assert table[0]["vote"] == 25 and table[3]["vote"] == 26 and table[7]["vote"] == 27
    assert table[1]["vote"] == 24
    assert change["accuracy_ceiling_ratio"] < 8
    assert analysis["box"]["correct_boxes"] == 202
    assert analysis["box"]["boxes_by_start_quartile"]["0.75"] == 0
    assert analysis["box"]["start_p50"] > 0.99
    if analysis["support"] is not None:
        assert all(item["correct_in_32"] == 0 for item in analysis["support"]["problems"])
        assert [item["mode_count_in_32"] for item in analysis["support"]["problems"]] == [16, 14, 23]
    OUT.write_text(json.dumps(analysis, indent=2) + "\n")
    print(json.dumps({k: analysis[k] for k in ("prefix", "single_sample_correct", "single_sample_mean", "log_change_n1_to_n8", "A_over_tau_ratio_n8_over_n1", "length", "bootstrap_A_over_tau", "max_completion_tokens", "support")}, indent=2))


if __name__ == "__main__":
    main()
