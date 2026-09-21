# Experiments

The note in `src/stu.md` reports structural task utilization for test-time scaling on Qwen3-4B-Thinking-2507. With \(\alpha=1\) and with attention and relevance unmeasured, the reported score is \(A/\tau\).

Python 3.10 or newer. The runners use the standard library. Generation goes through a local vLLM server.

## What is reported

| Script | What it measures |
| --- | --- |
| `run_small.py` | Easy GSM8K and medium MATH width, verifier ratings, short reflection |
| `run_enrich.py` | Generation caps 128–1024, and a 2048-token critique |
| `run_aime.py` | AIME 2025 at a 10240-token cap, temperature 1.0 |
| `run_aime_full.py` | AIME 2025 at 81920 tokens, temperature 0.6, top-k 20 |
| `run_support.py` | 24 further draws on AIME problems 13, 14, and 15 |
| `analyze.py` | Recomputes the AIME table in the note from saved traces |

`metrics.py` is the vote, the token count, and the bootstrap. Ties break toward the smaller integer. `analyze.py` recomputes the AIME table, the split between problems wrong at one sample and problems that are merely not unanimous, and the position of the correct box. Run the scripts from this directory.

Width comparisons do not match token budgets. The matched-budget comparison is reflection against a resample. The medium band enters only if some later sample in the pool is correct, so Pass at width 16 on that band is the entry rule.

## Serve the model

Eight GPUs, one server each, context 90112 so an 81920-token completion fits with the prompt. Set `VLLM_PYTHON` to the interpreter that has vLLM, and `VLLM_MODEL` to the checkpoint, then:

```bash
bash start_vllm.sh
```

Servers listen on ports 8000–8007. The client round-robins those ports.

## Contest run

```bash
python3 run_aime_full.py
python3 analyze.py
```

`run_aime_full.py` writes `results/aime_full/generations.jsonl` and resumes from it. `analyze.py` writes `results/aime_full/analysis.json` and checks the headline counts: vote 25, 24, 26, 27 at widths 1, 2, 4, and 8.

The short checks share seed 1234 and temperature 1.0. The contest run does not. Do not pool those traces into one table.

## Files that are not the protocol

`legacy/` holds earlier runners that were not used for the numbers in the note.
