# 7. 三组实验对照与比较方式

## Experiment 1 — Pure-4B Heavy Pipeline

| 项 | 设置 |
|----|------|
| Solver | Qwen3-4B-Thinking-2507 |
| Verifier | Qwen3-4B-Thinking-2507 |
| Search | 统一 Heavy Pipeline 参数 |
| 诊断 | generation 能力 vs 4B self-verification |

## Experiment 2 — Strong-Verifier Heavy Pipeline

| 项 | 设置 |
|----|------|
| Solver | Qwen3-4B-Thinking-2507（与 Exp1 相同） |
| Verifier | DeepSeek-V4-Flash |
| Search | **与 Exp1 完全相同**（只换 verifier） |
| 诊断 | verifier bottleneck：强 verifier 能否更好挑出正确解 |

## Experiment 3 — STOP

| 项 | 设置 |
|----|------|
| Solver | Qwen3-4B-Thinking-2507 |
| Verifier | DeepSeek-V4-Flash |
| Checkpoints | 4k / 8k / 12k / 16k prefix |
| 诊断 | online verification efficiency：更少计算量下能否达到同等或更高 accuracy |

## 比较方式

1. **Exp1 vs Exp2（隔离 verifier）**  
   同一 solver、同一 search budget；比较最终 AIME accuracy 与选中 proof 的 verification score 分布。若 Exp2 显著高于 Exp1，支持「瓶颈在 verification / selection」。

2. **Exp2 vs Exp3（隔离 STOP）**  
   同一强 verifier；比较 accuracy–compute Pareto：是否在更低 verifier 调用量下达到 ≥ Exp2 的 accuracy。

3. **主指标统一**  
   一律报告 \(\text{Accuracy} = \text{正确题数}/30\)，并按 [metrics/definitions.md](../metrics/definitions.md) 填写结果模板。

## 结果模板

| Experiment | Accuracy ( /30 ) | Accuracy (%) | Verifier calls (approx.) | Notes |
|------------|------------------|--------------|--------------------------|-------|
| Exp1 Pure-4B | | | | |
| Exp2 Strong-Verifier | | | | |
| Exp3 STOP @4k | | | | |
| Exp3 STOP @8k | | | | |
| Exp3 STOP @12k | | | | |
| Exp3 STOP @16k | | | | |
