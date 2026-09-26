# Verifier Bottleneck for Math LLMs

> **Research Note:** [GitHub Pages](https://jing524.github.io/Verifier-Bottleneck-for-Math-LLMs/) ·
> **Blog Branch:** [blog](https://github.com/Jing524/Verifier-Bottleneck-for-Math-LLMs/tree/blog)

This repository studies whether additional **test-time sampling** for mathematical reasoning models improves accuracy fast enough to justify the extra reasoning tokens.

The project focuses on three related questions:

1. **Generation** — does a correct answer appear in the candidate pool?
2. **Selection** — if a correct candidate exists, can voting or a verifier identify it?
3. **Utilization** — is the resulting accuracy gain worth the additional inference cost?

The accompanying research note proposes **Structural Task Utilization (STU)** as a framework for describing these trade-offs.

$$ \mathrm{STU} = \frac{A\beta\rho}{\alpha\tau} $$

where $\tau=T/1024$ is the normalized token cost.

---

## Key Findings

- On **AIME 2025**, one sample from Qwen3-4B-Thinking-2507 solves **25/30 problems (83.3%)**.
- An **8-sample majority vote** solves **27/30 problems (90.0%)**.
- Accuracy improves by only **1.08×**, while tokens per problem increase by **8.15×**.
- As a result, $A/\tau$ at 8 samples is only about **13.2%** of the one-sample value.
- On a diagnostic medium-difficulty set, coverage improves from **6/12 to 12/12**, while $A/\tau$ falls from **0.136 to 0.017**.
- Three AIME problems remain unsolved after **32 samples each**, while particular wrong answers repeatedly dominate the output distribution.
- A verifier does not always recover correct solutions that already exist in the candidate pool.
- In a small matched-budget experiment, reflection and independent resampling both achieve **7/8** accuracy.

> **Main observation:** More test-time compute can improve capability without necessarily improving utilization.

---

## Structural Task Utilization

We define Structural Task Utilization as:

$$ \mathrm{STU} = \frac{A\beta\rho}{\alpha\tau} $$

| Symbol | Meaning |
| --- | --- |
| $A$ | Exact-answer accuracy |
| $\beta$ | Share of attention assigned to answer-relevant tokens |
| $\rho$ | Fraction of read tokens that are relevant to the answer |
| $\alpha$ | Activated-parameter ratio |
| $\tau$ | Normalized token cost, with $\tau=T/1024$ |

The current experiments directly measure $A$ and $\tau$.

The factors $\beta$ and $\rho$ are **not yet directly measured**. Since the main model used here, Qwen3-4B-Thinking-2507, is dense, $\alpha=1$.

Therefore, the empirical score reported in the current experiments is primarily:

$$ \frac{A}{\tau} $$

rather than full STU.

The division by 1024 only changes the unit in which token cost is expressed. It does not change the relative comparison between methods.

---

## Pass@n vs. Vote@n

When multiple reasoning samples are generated for the same problem, two different quantities matter.

### Pass@n

**Pass@n** asks:

> Does at least one of the first $n$ samples contain the gold answer?

Here, the **gold answer** is the ground-truth answer for the problem.

Pass@n therefore measures the **coverage of the candidate pool**.

For example, suppose the gold answer is `81` and the first two samples produce:

```text
Sample 1: 70
Sample 2: 81
Gold:     81
```

Then Pass@2 succeeds because the correct answer appears somewhere in the first two samples.

### Vote@n

**Vote@n** asks:

> Does majority voting over the first $n$ samples return the gold answer?

Vote@n therefore depends on both:

1. whether a correct candidate was generated, and
2. whether the selection rule actually chooses it.

For example, on AIME 2025 at $n=2$:

- **Pass@2 = 26** means that 26 of the 30 problems have at least one correct candidate among their first two samples.
- **Vote@2 = 24** means that majority voting over those two samples returns the correct answer on only 24 of the 30 problems.

Thus, the correct answer may already exist in the candidate pool without being selected correctly.

This distinction separates **generation coverage** from **selection quality** and motivates the verifier-bottleneck analysis.

---

## Why Sampling Width Can Reduce Utilization

Suppose each independently generated reasoning trace is correct with probability $p$.

The probability that at least one of $n$ samples is correct is:

$$ \mathrm{Pass@}n = 1-(1-p)^n $$

Coverage therefore increases with sampling width.

However, if token cost grows approximately linearly with the number of samples,

$$ \tau(n) \propto n $$

and $\beta$, $\rho$, and $\alpha$ remain fixed, then:

$$ \mathrm{STU}(n) \propto \frac{1-(1-p)^n}{n} $$

The numerator approaches 1 as $n$ increases, while the denominator continues to grow approximately linearly.

This creates the central tension studied in this repository:

> **Candidate coverage can increase while utilization decreases.**

---

## Main Results

### AIME 2025

| Width $n$ | Pass@n | Vote@n | Tokens / problem | $A/\tau$ |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 25 | 25 | 22,247 | 0.0384 |
| 2 | 26 | 24 | 43,533 | 0.0188 |
| 3 | 26 | 25 | 65,489 | 0.0130 |
| 4 | 26 | 26 | 88,859 | 0.0100 |
| 5 | 26 | 26 | 112,115 | 0.0079 |
| 6 | 27 | 26 | 134,349 | 0.0066 |
| 7 | 27 | 26 | 157,533 | 0.0056 |
| 8 | 27 | 27 | 181,335 | 0.0051 |

From one sample to eight samples:

| Quantity | Change |
| --- | ---: |
| Accuracy | 83.3% → 90.0% |
| Accuracy ratio | 1.08× |
| Token ratio | 8.15× |
| Relative $A/\tau$ | 0.132× |

The additional samples improve accuracy, but the read cost grows much faster than the accuracy gain.

Even a perfect 30/30 result could improve accuracy from the one-sample baseline by at most:

$$ \frac{30}{25} = 1.20 $$

which is still far below the approximately 8× increase in sampling width.

---

### Diagnostic Width Experiment

| Setting | Accuracy / Pass | Tokens / problem | $A/\tau$ |
| --- | ---: | ---: | ---: |
| Easy, $n=1$ | 12/12 | 618 | 1.658 |
| Easy, $n=16$ | 12/12 | 9,808 | 0.104 |
| Medium, $n=1$ | 6/12 | 3,771 | 0.136 |
| Medium, $n=16$ | 12/12 | 58,728 | 0.017 |

The **easy set** shows the pure cost of redundant sampling: accuracy is already perfect with one sample, while additional samples only increase the read cost.

The **medium set** shows a more interesting case: additional samples genuinely improve coverage from 6/12 to 12/12, but the gain still grows much more slowly than token cost.

---

## Experimental Story

The experiments are organized around a sequence of increasingly difficult questions about test-time compute.

### 1. Short-Budget Test

**Question:** Is additional test-time compute useful when a single reasoning trajectory has not yet had enough space to finish?

Generation caps of 128, 256, 512, and 1024 tokens are evaluated on easy problems.

At short budgets, many traces cannot finish. Increasing the generation allowance from 512 to 1024 substantially improves accuracy, while actual token usage grows only slightly because completed traces stop early.

This distinguishes two different forms of test-time scaling:

- giving one reasoning trajectory enough space to finish;
- generating additional independent reasoning trajectories.

The first can improve utilization when the original trace is prematurely truncated.

---

### 2. Parallel-Width Scaling

**Question:** What happens when we increase the number of independent reasoning samples?

The experiment evaluates sampling widths:

$$ n \in \{1,2,4,8,16\} $$

and tracks:

- Pass@n,
- majority-vote accuracy,
- verifier-selected accuracy,
- token cost,
- and $A/\tau$.

On easy problems, accuracy is already perfect with one sample, so wider pools mostly duplicate computation.

On the diagnostic medium set, coverage improves substantially with width, but token cost grows more quickly than accuracy.

---

### 3. Verifier Selection

**Question:** If the correct answer already exists in the candidate pool, can a verifier identify it?

Each candidate solution receives multiple verifier ratings.

Across the diagnostic pool, correct and incorrect solutions receive similar mean ratings:

- Correct solutions: **0.864**
- Incorrect solutions: **0.812**

The score therefore provides only weak separation between correct and incorrect reasoning traces.

This leads to the central **verifier bottleneck**:

> A correct solution may already exist in the candidate pool without being reliably identified by the selector.

---

### 4. Answer Position and Early Stopping

**Question:** Can token cost be reduced simply by stopping reasoning earlier?

The final correct boxed answer usually appears very close to the end of the generated reasoning trace:

- Easy: median position ≈ **99.2%**
- Medium: median position ≈ **99.8%**
- AIME: median position ≈ **99.97%**

Simple prefix truncation therefore tends to remove the final answer rather than remove only unnecessary reasoning.

This observation does **not** imply that every preceding token is necessary.

It only shows that naive stopping based on output position is insufficient.

---

### 5. Reflection vs. Resampling

**Question:** Instead of generating another independent solution, can the model critique and revise its existing reasoning more efficiently?

The reflection pipeline is:

```text
Initial solution
       ↓
    Critique
       ↓
     Rewrite
       ↓
  Final answer
```

The comparison uses an approximately matched token budget.

With the longer critique setting:

- Reflection: **7/8**
- Matched independent resampling: **7/8**

The two methods fail on different problems.

This small pilot experiment therefore does not show a clear accuracy advantage for reflection over additional independent sampling.

---

### 6. AIME 2025

**Question:** Does the same utilization pattern appear on a full competition benchmark?

The final AIME experiment uses Qwen3-4B-Thinking-2507 with contest-style sampling:

- temperature: `0.6`
- top-p: `0.95`
- top-k: `20`
- maximum new tokens: `81920`

For all 30 AIME 2025 problems, eight independent samples are generated.

This produces:

$$ 30 \times 8 = 240 $$

reasoning traces.

All 240 traces finish normally.

The main comparison is:

```text
1 sample
25 / 30 correct
≈ 22k tokens / problem

8-sample majority vote
27 / 30 correct
≈ 181k tokens / problem
```

Accuracy improves, but the additional read cost is much larger.

---

### 7. Stable Error Modes

**Question:** Are persistent failures simply caused by insufficient sampling width?

Three AIME problems have no correct candidate among their first eight samples.

Each problem is therefore extended from 8 to 32 total samples.

The gold answer still never appears.

Instead, particular wrong answers repeatedly dominate:

| Problem | Gold | Dominant wrong answer | Frequency in 32 samples |
| ---: | ---: | ---: | ---: |
| 13 | 204 | 79 | 16 |
| 14 | 60 | 63 | 14 |
| 15 | 735 | 147 | 23 |

These observations do not prove that the gold answer has zero probability under the model.

They do show that the failures are structured rather than uniformly random: the model repeatedly returns to stable wrong-answer modes.

---

## Three Bottlenecks

The experiments suggest three distinct bottlenecks.

### Generation Bottleneck

The correct answer may fail to appear even after many independent samples.

This is observed in the three AIME problems that remain incorrect after 32 samples.

### Selection Bottleneck

The correct answer may already exist in the pool, but voting or a verifier may fail to select it.

The difference between Pass@n and Vote@n directly reflects this gap.

### Utilization Bottleneck

Even when final accuracy improves, the gain may be much smaller than the increase in read cost.

This is reflected by the decline in $A/\tau$ as sampling width increases.

Together:

```text
More test-time compute
        ↓
More reasoning samples
        ↓
Candidate coverage may improve
        ↓
Selection may still fail
        ↓
Some problems remain trapped in stable wrong modes
        ↓
Token cost continues to grow
        ↓
Accuracy can improve while utilization falls
```

---

## Experimental Setup

### Model

Main model:

`Qwen3-4B-Thinking-2507`

The model is dense, so:

$$ \alpha = 1 $$

### Serving

- vLLM
- 8 GPUs
- one server per GPU
- ports `8000`–`8007`

### AIME Sampling

- temperature: `0.6`
- top-p: `0.95`
- top-k: `20`
- maximum new tokens: `81920`

### Short Experiments

- temperature: `1.0`
- top-p: `0.95`
- seed: `1234`

### Token Accounting

Token cost is defined as:

$$ T = \text{prompt tokens} + \text{solution completion tokens} $$

and:

$$ \tau = \frac{T}{1024} $$

Verifier inference tokens are currently **not included** in $\tau$.

---

## Repository Layout

| Path | Role |
| --- | --- |
| `experiments/metrics.py` | Voting, token accounting, $A/\tau$, and bootstrap intervals |
| `experiments/analyze.py` | Rebuilds the AIME tables and answer-position analysis from local traces |
| `experiments/run_aime_full.py` | Main AIME 2025 experiment with an 81920-token generation cap |
| `experiments/run_small.py` | Easy/medium width scaling, verifier ratings, and short reflection |
| `experiments/run_enrich.py` | Short generation-budget tests and longer critique experiments |
| `experiments/run_support.py` | Additional samples for the three persistent AIME failures |
| `experiments/start_vllm.sh` | Starts one vLLM server per GPU |

`experiments/README.md` contains the detailed experimental runbook.

The `legacy/` directory contains earlier runners that are **not part of the final reported protocol**.

---

## Reproducing the AIME Analysis

### 1. Start the vLLM servers

Set `VLLM_PYTHON` and `VLLM_MODEL`, then run:

```bash
bash experiments/start_vllm.sh
```

### 2. Run the full AIME experiment

```bash
python3 experiments/run_aime_full.py
```

### 3. Recompute the analysis

```bash
python3 experiments/analyze.py
```

The analysis checks the headline majority-vote counts:

| Width | Vote |
| ---: | ---: |
| $n=1$ | 25 |
| $n=2$ | 24 |
| $n=4$ | 26 |
| $n=8$ | 27 |

### Raw Traces

Raw generation traces are not currently included in the repository.

`experiments/analyze.py` expects them locally under:

```text
experiments/results/
```

Reproducing the full trace-level analysis therefore requires rerunning the model.

---

## Limitations

The current study has several important limitations:

- The main experiments use a single reasoning model, Qwen3-4B-Thinking-2507.
- AIME 2025 contains only 30 problems.
- $\beta$ and $\rho$ are not directly measured, so the experiments report $A/\tau$ rather than full STU.
- Verifier inference tokens are not included in $\tau$.
- The medium-difficulty set is a diagnostic subset selected to contain problems recoverable by later samples.
- The reflection comparison contains only eight problems and should be treated as a pilot experiment.
- Raw generation traces are not currently distributed with the repository.
- The current results should not be interpreted as showing that all forms of test-time scaling reduce utilization.

---

## Next Steps

The main open problem is to move from token-level efficiency toward direct measurement of **internal model utilization**.

### Measure $\rho$

Identify which parts of a reasoning trace actually contribute to the final answer.

Possible directions include causal deletion, span ablation, counterfactual reasoning edits, or minimal sufficient reasoning subsets.

### Measure $\beta$

Study whether the model's internal attention or computation concentrates on answer-relevant information.

This would move the project from an $A/\tau$ analysis toward direct measurement of full STU.

### Characterize Generation Bottlenecks

Study stable wrong-answer modes and determine whether they correspond to persistent reasoning basins in the model's generation distribution.

### Characterize Selection Bottlenecks

Measure how much candidate coverage is lost because of imperfect majority voting or verifier-based selection.

### Cross-Model Evaluation

Extend the framework to:

- larger dense reasoning models;
- sparse models;
- Mixture-of-Experts models;
- different verifier architectures.

### Matched-Compute Comparisons

Compare:

- parallel sampling;
- reflection;
- adaptive sampling;
- verifier-guided sampling;
- early stopping;
- reasoning compression;

under matched token or compute budgets.

---

## Research Note

The rendered research note is available online:

[https://jing524.github.io/Verifier-Bottleneck-for-Math-LLMs/](https://jing524.github.io/Verifier-Bottleneck-for-Math-LLMs/)

The source is maintained on the `blog` branch:

```bash
git checkout blog
python3 build_site.py
```

Then open:

```text
index.html
```

---

## License

MIT License.
