# Verifier Bottleneck for Math LLMs

Code for the structural task utilization note. On one model the reported score is \(A/\tau\): exact-answer accuracy divided by tokens read, in units of 1024.

$$
\mathrm{STU}=\frac{A\cdot\beta\cdot\rho}{\alpha\cdot\tau}
$$

The rendered note is on the `blog` branch and at the GitHub Pages site. This branch is the code.

## Layout

| Path | Role |
| --- | --- |
| `experiments/metrics.py` | Vote, token count, \(A/\tau\), bootstrap |
| `experiments/analyze.py` | Rebuilds the AIME table and the box-position check from local traces |
| `experiments/run_aime_full.py` | AIME 2025 at 81920 tokens, temperature 0.6, top-k 20 |
| `experiments/run_small.py` | Easy and medium width, verifier ratings, short reflection |
| `experiments/run_enrich.py` | Generation caps 128–1024, and a longer critique |
| `experiments/run_support.py` | Further draws on the three AIME problems missed by eight samples |
| `experiments/start_vllm.sh` | One server per GPU |

`experiments/README.md` is the runbook. Raw generation traces are not in the repository. `analyze.py` expects them on disk under `experiments/results/`.

## Reproduce the contest table

From `experiments/`, with the servers already up:

```bash
python3 analyze.py
```

That checks the headline counts: vote 25, 24, 26, and 27 at widths 1, 2, 4, and 8.

## Note

```bash
git checkout blog
python3 build_site.py
```

Open `index.html`.
