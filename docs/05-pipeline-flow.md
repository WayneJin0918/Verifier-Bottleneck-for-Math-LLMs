# 5. Heavy Pipeline 完整实验流程

## 5.1 初始生成

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

## 5.2 Verification

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

## 5.3 Verification score 聚合

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
