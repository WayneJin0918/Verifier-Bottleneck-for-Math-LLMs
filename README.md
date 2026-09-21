# Verifier Bottleneck for Math LLMs

Structural task utilization for test-time scaling. On one model the reported score is \(A/\tau\): exact-answer accuracy divided by tokens read, in units of 1024.

$$
\mathrm{STU}=\frac{A\cdot\beta\cdot\rho}{\alpha\cdot\tau}
$$

The note is this branch. Open `index.html`, or edit `src/stu.md` and rebuild:

```bash
python3 build_site.py
```

The contest comparison is AIME 2025 with Qwen3-4B-Thinking-2507 at the model card's sampler and length. One sample scores 25 of 30. A vote over eight scores 27 of 30, and \(A/\tau\) falls. Reproduce that table from `experiments/`:

```bash
python3 analyze.py
```

Research notes under `docs/` and `metrics/` stay on the local machine and are not tracked. Generation traces are local as well. `experiments/README.md` is the runbook.
