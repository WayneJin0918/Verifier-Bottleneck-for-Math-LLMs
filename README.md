# Verifier Bottleneck for Math LLMs

**Test-time scaling is not “more samples, higher accuracy.”** Extra attempts only count if activated parameters, attention, and the tokens being read are spent on the answer.

\[
\mathrm{STU}=\frac{A\cdot\beta\cdot\rho}{\alpha\cdot\tau}
\]

Structural Task Utilization (STU) is the score. Parallel sampling and serial reflection are the two ways to spend test-time compute. This repo specifies how to tell them apart on AIME 2025.

| Factor | What it measures | In the score |
|--------|------------------|--------------|
| \(A\) | Exact-answer accuracy, 30 AIME 2025 problems | numerator |
| \(\beta\) | Share of attention mass on tokens that matter to the answer | numerator |
| \(\rho\) | Share of tokens read that are actually about the answer | numerator |
| \(\alpha\) | Activated parameters / total parameters | denominator |
| \(\tau\) | Tokens read / 1024 | denominator |

A dense 4B verifier has \(\alpha=1\). DeepSeek-V4-Flash activates about 13B of 284B parameters, so \(\alpha\approx 0.0458\). A lower ratio is a smaller structural price per token. It is not a smaller FLOP count: Flash still activates more parameters in absolute terms than the 4B model. Both numbers are reported.

Verification score only ranks candidate proofs. It is not STU, and it is not the submitted answer.

## Why parallel and serial

Two knobs scale test-time compute. They do not move STU the same way.

**Parallel.** Draw \(n\) independent proofs, verify each, keep the best. Width is \(n\in\{1,4,16,64\}\). A new sample usually adds a full trajectory. If that trajectory is a dead branch, \(\rho\) falls and \(\tau\) rises while \(\alpha\) stays fixed. Accuracy can go up and STU can go down.

**Serial reflection.** Keep one trajectory and rewrite it for \(r\in\{0,1,2,4,8,16\}\) rounds. Each round, the verifier reads the current proof (or an early prefix) and the solver revises. This is the reflection loop, including STOP checks at 4k / 8k / 12k / 16k tokens. A useful round moves attention onto the failing step (\(\beta\) up) and replaces tokens that were not about the answer (\(\rho\) up). A useless round is just another long read.

Heavy Pipeline at \(n=64\), one proof refined, up to 16 rounds, is a single cell of this grid, not the experiment.

Compare cells at matched tokens read, or matched activated-parameter tokens. The claim is that STU and accuracy do not rank the cells in the same order, and that the gap is carried by \(\beta\), \(\rho\), or \(\alpha\). If they always agree, STU is not adding information and the claim fails.

## What is held fixed

AIME 2025 (30 problems), the Qwen3-4B-Thinking-2507 solver, the generation prompt, answer extraction, temperature 1.0, top-p 0.95, generation length, and the AIME exact-match evaluator. The verifier is either the same 4B model or DeepSeek-V4-Flash. Only one of those changes at a time, so a gain cannot be attributed to a different search budget.

## Docs

| | |
|--|--|
| [Metric](metrics/definitions.md) | Formal definition of STU |
| [Parallel vs serial protocol](docs/07-experiments.md) | The grid, matched-budget comparison, and what would falsify the claim |
| [Blog plan](docs/08-blog-plan.md) | The additional experiments required before a research blog |
| [Theory](docs/09-theory.md) | Identities and the parallel-width proposition behind those experiments |
| [Goals](docs/01-goals.md) | What the three questions are |
| [Models](docs/03-models.md) | Solver and the two verifiers |
| [Heavy Pipeline cell](docs/04-heavy-pipeline-params.md) | The locked \((n=64, r\le 16)\) setting |
| [Flow](docs/05-pipeline-flow.md) | Generate, verify, aggregate |
| [Reflection step](docs/06-refinement.md) | One serial round |
| [Authors](AUTHORS.md) | Jing Huang, Jiaxi Bi, Tongxu Luo, Benyou Wang (corresponding) |

The writeup covers the experimental idea, the metric, and the controls. It does not describe repository layout, output paths, or how any run was recovered.

## License

[MIT](LICENSE)
