# DeepSeekMath-V2 Heavy Pipeline × STOP 实验方案梳理

本文只整理实验本身的研究思路、流程、参数、对照关系、已有结果与后续比较方式，不包含项目路径、目录结构、输出路径、代码恢复过程等工程细节。

## 核心 Metric

最终任务指标为 **AIME exact-answer accuracy**：

\[
\text{Accuracy} = \frac{\text{正确题数}}{30}.
\]

Verification score（用于候选排序，非最终答案投票）：

\[
s(p) = \frac{1}{64}\sum_{i=1}^{64} r_i,\qquad r_i\in\{0, 0.5, 1\}.
\]

研究递进关系：

\[
\boxed{
\text{Generator potential}
\rightarrow
\text{Verifier bottleneck}
\rightarrow
\text{Online verification efficiency}
}
\]

---

## 1. 实验目标

整个项目围绕 DeepSeekMath-V2 的 Heavy Pipeline / High-Compute Search 展开，核心目标不是单纯追求更高的 AIME 分数，而是分析：

1. 小模型 solver 在大量采样下到底有没有生成正确解的能力；
2. Heavy Pipeline 的瓶颈究竟来自 generation 还是 verification / selection；
3. 将 verifier 从 Qwen3-4B 替换成更强的 DeepSeek-V4-Flash 后，是否能更好地从候选中找出正确解；
4. 在使用强 verifier 的基础上，引入 STOP 风格的中途检查，是否能够用更少计算量达到相同或更高的最终准确率。

因此整个实验不是三个互不相关的实验，而是一个递进关系：

```
Experiment 1
Pure-4B Heavy Pipeline
Qwen3-4B Solver + Qwen3-4B Verifier
        |
        | 诊断 generation 与 self-verification
        v
Experiment 2
Strong-Verifier Heavy Pipeline
Qwen3-4B Solver + DeepSeek-V4-Flash Verifier
        |
        | 控制 verifier strength
        v
Experiment 3
STOP
Qwen3-4B Solver + DeepSeek-V4-Flash Verifier
4k / 8k / 12k / 16k prefix checkpoints
```

对应三个核心研究问题：

| 阶段 | 研究问题 |
|------|----------|
| Generator potential | 小模型在大量采样下是否具备生成正确解的能力 |
| Verifier bottleneck | 瓶颈在 generation 还是 verification / selection |
| Online verification efficiency | 强 verifier + STOP 中途检查能否以更少计算量达到同等或更高准确率 |

---

## 2. 数据集与评测对象

所有核心实验统一使用：

| 项 | 值 |
|----|-----|
| Dataset | AIME 2025 |
| Number of problems | 30 |
| Primary metric | AIME exact-answer accuracy = 正确题数 / 30 |

为了保证不同实验之间可比较，以下内容应保持一致：

- 数据集
- solver checkpoint
- generation prompt
- answer extraction
- temperature
- top-p
- generation max length
- Heavy Pipeline search budget
- 最终 AIME evaluator

---

## 3. 模型设置

### 3.1 Solver

统一使用：

```
Qwen3-4B-Thinking-2507
```

职责：

- 初始 proof / reasoning generation
- Heavy Pipeline 中的 refinement / regeneration
- STOP 实验中的 reasoning continuation

### 3.2 Pure-4B Baseline Verifier（Experiment 1）

```
Verifier = Qwen3-4B-Thinking-2507
```

即：

```
Solver = 4B
Verifier = 4B
```

目的是得到一个完全由 4B 模型构成的 Heavy Pipeline baseline。

### 3.3 Strong Verifier（Experiment 2 & 3）

```
DeepSeek-V4-Flash
```

| 项目 | 配置 |
|------|------|
| 架构 | MoE |
| Total parameters | 约 284B |
| Activated parameters | 约 13B |
| 精度 | FP4 + FP8 mixed |
| 本地权重 | 约 149GB |

职责：

- Experiment 2：对完整 proof 做 verification
- Experiment 3：对中途 reasoning prefix 做 verification / continuation judgment

---

## 4. Heavy Pipeline 统一核心参数

目前锁定的 Heavy Pipeline 参数如下。这些参数构成所有 Heavy Pipeline baseline 的共同 search setting。

| 参数 | 值 |
|------|-----|
| `n_parallel_proof_gen` | 64 |
| `n_verification_per_proof` | 64 |
| `n_best_proofs_to_sample` | 64 |
| `n_proofs_to_refine` | 1 |
| `n_agg_trials` | 64 |
| `max_ratings_per_score` | 4 |
| `max_rounds` | 16 |
| `proof_gen_temp` | 1.0 |
| `proof_verification_temp` | 1.0 |
| `top_p` | 0.95 |
| `proof_gen_max_len` | 131072 |
| `proof_verification_max_len` | 65536 |
| `seed` | 1234 |

**Experiment 2 的关键原则：** 只替换 verifier，不改变 Heavy Pipeline 的搜索参数。

这样才能把：

```
4B self-verifier
vs
DeepSeek-V4-Flash verifier
```

的效果单独隔离出来。

---

## 5. Heavy Pipeline 完整实验流程

### 5.1 初始生成

对每一道 AIME 题，由 solver 独立生成 **64 candidate proofs**。

因此 30 道题共生成：

\[
30 \times 64 = 1920
\]

条初始候选。

```
Problem
  |
  v
Qwen3-4B Solver
  |
  | temperature = 1.0
  | top_p = 0.95
  | n = 64
  v
64 candidate proofs
```

### 5.2 Verification

每一个候选 proof 都进行 **64 independent verification rollouts**。

因此第一轮 verification 调用数量为：

\[
30 \times 64 \times 64 = 122{,}880
\]

即：

```
30 problems
× 64 proofs/problem
× 64 verifier rollouts/proof
= 122,880 verifier outputs
```

这是整个 Heavy Pipeline 中最重的计算部分。

### 5.3 Verification score 聚合

当前实验中 verifier 原始 rating 取值表现为：

```
0.0
0.5
1.0
```

对同一个 proof 的 64 个 ratings 聚合成一个 verification score。

根据已有结果可以高置信认为其形式近似：

\[
s(p) = \frac{1}{64}\sum_{i=1}^{64} r_i,\qquad r_i\in\{0, 0.5, 1\}.
\]

例如曾出现：

\[
s = 0.9921875 = \frac{63\times 1 + 1\times 0.5}{64}.
\]

因此 verification 的作用是给 candidate proof **排序**，而不是直接使用 final answer majority vote。

---

## 6. Refinement 的实验逻辑

Heavy Pipeline 不只做：

```
generate -> verify -> choose
```

还包含后续 refinement。

总体逻辑：

```
Initial candidate pool
        |
        v
Verification + ranking
        |
        v
Select proof(s) requiring refinement
        |
        v
Qwen3-4B regenerate / refine
        |
        v
New candidate proofs
        |
        v
Verification again
        |
        v
Update candidate pool
```

---

## 文档结构

| 文件 | 内容 |
|------|------|
| [README.md](README.md) | 总览与核心 metric（本文） |
| [docs/01-goals.md](docs/01-goals.md) | 实验目标与递进关系 |
| [docs/02-dataset-metric.md](docs/02-dataset-metric.md) | 数据集与评测 metric 定义 |
| [docs/03-models.md](docs/03-models.md) | Solver / Verifier 设置 |
| [docs/04-heavy-pipeline-params.md](docs/04-heavy-pipeline-params.md) | 统一搜索参数 |
| [docs/05-pipeline-flow.md](docs/05-pipeline-flow.md) | 生成、验证、聚合流程 |
| [docs/06-refinement.md](docs/06-refinement.md) | Refinement 逻辑 |
| [docs/07-experiments.md](docs/07-experiments.md) | 三组实验对照与比较方式 |
| [metrics/definitions.md](metrics/definitions.md) | Metric 形式化定义（可复用对照表） |
