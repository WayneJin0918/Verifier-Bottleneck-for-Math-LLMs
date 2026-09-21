# Metric 形式化定义

本文档单独抽出本实验方案中的全部可比较指标，便于跨 Experiment 1 / 2 / 3 对齐口径。

## 1. 主指标：AIME Exact-Answer Accuracy

| 字段 | 定义 |
|------|------|
| 名称 | `aime_exact_answer_accuracy` |
| 数据集 | AIME 2025 |
| \(N\) | 30 |
| 公式 | \(\text{Accuracy} = \dfrac{\#\{\text{problems with exact correct answer}\}}{30}\) |
| 答案判定 | exact-answer match（与统一 AIME evaluator 一致） |
| 用途 | 所有实验的最终任务指标 |

### 可比性约束（必须一致）

- 数据集
- solver checkpoint
- generation prompt
- answer extraction
- temperature / top-p / generation max length
- Heavy Pipeline search budget
- 最终 AIME evaluator

任一上述项变化时，不得直接横向比较 accuracy。

---

## 2. Verification Score（候选排序分）

| 字段 | 定义 |
|------|------|
| 名称 | `verification_score` |
| 记法 | \(s(p)\) |
| 输入 | 同一 proof \(p\) 的 \(K\) 次独立 verification ratings |
| \(K\) | 64（`n_verification_per_proof` / `n_agg_trials`） |
| 单次 rating | \(r_i \in \{0.0, 0.5, 1.0\}\) |
| 聚合 | \(s(p) = \dfrac{1}{K}\sum_{i=1}^{K} r_i\) |
| 取值范围 | \([0, 1]\) |
| 用途 | 对 candidate proofs **排序 / 选择**，不是最终答案 majority vote |

### 实例校验

曾观测到：

\[
s = 0.9921875 = \frac{63\times 1 + 1\times 0.5}{64}
\]

与 mean-of-ratings 形式一致。

### 与最终答案的关系

| 信号 | 是否作为最终提交答案 |
|------|----------------------|
| verification score \(s(p)\) | 否（仅排序） |
| selected proof 的 extracted answer | 是（经 AIME evaluator） |
| answer majority vote over proofs | 否（本方案不以此为主） |

---

## 3. 计算量相关辅助 Metric（用于 STOP 效率比较）

在 Experiment 3（STOP）中，除 accuracy 外，建议报告以下效率相关量，以便回答「更少计算量是否达到相同或更高准确率」。

| 名称 | 定义意图 |
|------|----------|
| `n_initial_candidates` | \(30 \times 64 = 1920\) 初始 proofs |
| `n_verifier_calls_round1` | \(30 \times 64 \times 64 = 122{,}880\)（Heavy Pipeline 第一轮 verification） |
| `prefix_checkpoint_tokens` | STOP 中途检查点：4k / 8k / 12k / 16k |
| `verifier_calls_total` | 含 refinement / STOP 中途检查后的 verifier 总调用次数 |
| `accuracy_vs_compute` | 以 `verifier_calls_total`（或等价 compute proxy）为横轴、accuracy 为纵轴的 Pareto 比较 |

> 注：本文档只定义口径；具体数值以各实验跑完后的结果表填入。

---

## 4. 三组实验的对照 Metric 表

| Experiment | Solver | Verifier | Search budget | Primary metric | 诊断目标 |
|------------|--------|----------|---------------|----------------|----------|
| 1 Pure-4B | Qwen3-4B-Thinking-2507 | Qwen3-4B-Thinking-2507 | 统一 Heavy Pipeline | `aime_exact_answer_accuracy` | generation vs self-verification |
| 2 Strong-Verifier | Qwen3-4B-Thinking-2507 | DeepSeek-V4-Flash | 同 Exp1（只换 verifier） | `aime_exact_answer_accuracy` | verifier bottleneck |
| 3 STOP | Qwen3-4B-Thinking-2507 | DeepSeek-V4-Flash | 强 verifier + 4k/8k/12k/16k prefix | accuracy + compute efficiency | online verification efficiency |

### 隔离原则

- Exp1 → Exp2：只改变 verifier strength
- Exp2 → Exp3：在强 verifier 基础上引入 STOP 中途检查

递进关系：

\[
\text{Generator potential}
\rightarrow
\text{Verifier bottleneck}
\rightarrow
\text{Online verification efficiency}
\]

---

## 5. 结果填写模板（后续比较用）

| Experiment | Accuracy ( /30 ) | Accuracy (%) | Verifier calls (approx.) | Notes |
|------------|------------------|--------------|--------------------------|-------|
| Exp1 Pure-4B | | | ~122,880 (round1) + refine | |
| Exp2 Strong-Verifier | | | ~122,880 (round1) + refine | |
| Exp3 STOP @4k | | | | |
| Exp3 STOP @8k | | | | |
| Exp3 STOP @12k | | | | |
| Exp3 STOP @16k | | | | |
