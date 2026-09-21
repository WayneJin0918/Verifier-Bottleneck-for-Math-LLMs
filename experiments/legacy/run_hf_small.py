#!/usr/bin/env python3
"""Small theory run: eight GPUs, one Qwen3-4B each, no vLLM.

One sample of every AIME 2025 problem. Generation stops when an integer
is boxed, so the token count is the cost of producing an answer.
The parent then keeps a short special-case set for the theory note.
The 30-problem comparison is a later run.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

ROOT = Path("/opt/local/Verifier-Bottleneck-for-Math-LLMs/experiments")
MODEL = "/opt/local/ckpt/Qwen3-4B-Thinking-2507"
PROBLEMS = json.loads((ROOT / "aime2025.json").read_text())
OUT = ROOT / "results" / "hf_probe"
SEED = 1234
TEMP = 1.0
TOP_P = 0.95
TOP_K = 20
MAX_NEW = 12288
N_GPU = 8


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


def solve_prompt(problem: str) -> str:
    return (
        "Solve the following AIME problem. The answer is an integer from 0 to 999. "
        "Put the final answer in \\boxed{}.\n\n"
        f"{problem}"
    )


def worker(gpu: int, jobs: list[dict], out_path: str) -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu)
    time.sleep(gpu * 5)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList

    class BoxedStop(StoppingCriteria):
        def __init__(self, tokenizer, prompt_len: int):
            self.tokenizer = tokenizer
            self.prompt_len = prompt_len
            self.hit = False
            self.checked = 0

        def __call__(self, input_ids, scores, **kwargs):
            gen = input_ids[0, self.prompt_len :]
            n = int(gen.numel())
            if n < 8 or n - self.checked < 32:
                return False
            self.checked = n
            tail = self.tokenizer.decode(gen[-48:], skip_special_tokens=True)
            if re.search(r"boxed\{[^{}]*\d+[^{}]*\}", tail):
                self.hit = True
                return True
            return False

    tok = AutoTokenizer.from_pretrained(MODEL)
    torch.set_float32_matmul_precision("high")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL,
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        device_map="cuda:0",
    )
    model.eval()
    rows = []
    for job in jobs:
        messages = [{"role": "user", "content": solve_prompt(job["problem"])}]
        prompt = tok.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True,
        )
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        prompt_len = int(inputs["input_ids"].shape[1])
        stop = BoxedStop(tok, prompt_len)
        torch.manual_seed(int(job["seed"]))
        torch.cuda.manual_seed(int(job["seed"]))
        t0 = time.time()
        with torch.inference_mode():
            out = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW,
                do_sample=True,
                temperature=TEMP,
                top_p=TOP_P,
                top_k=TOP_K,
                pad_token_id=tok.pad_token_id,
                stopping_criteria=StoppingCriteriaList([stop]),
            )
        new_ids = out[0, prompt_len:]
        text = tok.decode(new_ids, skip_special_tokens=False)
        answer = extract_answer(text)
        row = {
            "idx": job["idx"],
            "sample": job["sample"],
            "seed": job["seed"],
            "gpu": gpu,
            "prompt_tokens": prompt_len,
            "completion_tokens": int(new_ids.shape[0]),
            "hit_cap": int(new_ids.shape[0]) >= MAX_NEW and not stop.hit,
            "boxed": stop.hit,
            "answer": answer,
            "gold": job["gold"],
            "correct": answer == job["gold"],
            "seconds": round(time.time() - t0, 3),
            "text": text,
        }
        rows.append(row)
        with open(out_path, "a") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(
            f"gpu {gpu} problem {job['idx']} tokens {row['completion_tokens']} "
            f"answer {answer} gold {job['gold']} correct {row['correct']}",
            flush=True,
        )


def select_cases(rows: list[dict]) -> dict:
    finished = [r for r in rows if r.get("answer") is not None and not r.get("hit_cap")]
    finished.sort(key=lambda r: r["completion_tokens"])
    unfinished = [r for r in rows if r.get("answer") is None]
    unfinished.sort(key=lambda r: r["completion_tokens"])
    cases = []
    for r in finished[:4]:
        role = "correct_and_short" if r["correct"] else "finished_but_wrong"
        cases.append(
            {
                "idx": r["idx"],
                "role": role,
                "tokens": r["completion_tokens"],
                "answer": r["answer"],
                "gold": r["gold"],
                "correct": r["correct"],
            }
        )
    if unfinished:
        r = unfinished[0]
        cases.append(
            {
                "idx": r["idx"],
                "role": "no_boxed_answer",
                "tokens": r["completion_tokens"],
                "answer": None,
                "gold": r["gold"],
                "correct": False,
            }
        )
    return {
        "max_new_tokens": MAX_NEW,
        "finished": len(finished),
        "correct": sum(1 for r in rows if r.get("correct")),
        "cases": cases,
        "note": (
            "Short correct problems are the case where one sample already has the answer, "
            "so extra parallel samples raise tokens read and cannot raise accuracy. "
            "A finished wrong answer is the case where another i.i.d. sample can change A. "
            "A missing box is the case where the budget is spent before an answer exists."
        ),
    }


def main() -> None:
    import multiprocessing as mp

    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for p in PROBLEMS:
        jobs.append(
            {
                "idx": p["idx"],
                "problem": p["problem"],
                "gold": int(p["answer"]),
                "sample": 0,
                "seed": SEED + int(p["idx"]),
            }
        )
    shards = [jobs[i::N_GPU] for i in range(N_GPU)]
    ctx = mp.get_context("spawn")
    procs = []
    shard_paths = []
    for gpu, shard in enumerate(shards):
        path = OUT / f"shard-{gpu}.jsonl"
        shard_paths.append(path)
        if path.exists():
            path.unlink()
        proc = ctx.Process(target=worker, args=(gpu, shard, str(path)))
        proc.start()
        procs.append(proc)
    failed = []
    for proc in procs:
        proc.join()
        if proc.exitcode != 0:
            failed.append((proc.pid, proc.exitcode))
    rows = []
    for path in shard_paths:
        if path.exists():
            rows.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    rows.sort(key=lambda r: r["idx"])
    (OUT / "probe.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    report = select_cases(rows)
    report["failed_processes"] = failed
    report["n"] = len(rows)
    (OUT / "cases.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "note"}, indent=2), flush=True)
    if failed:
        raise SystemExit(f"workers failed: {failed}")


if __name__ == "__main__":
    main()
