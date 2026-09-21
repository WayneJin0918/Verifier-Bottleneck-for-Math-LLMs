# 3. 模型设置

## 3.1 Solver

统一使用：

```
Qwen3-4B-Thinking-2507
```

职责：

- 初始 proof / reasoning generation
- Heavy Pipeline 中的 refinement / regeneration
- STOP 实验中的 reasoning continuation

## 3.2 Pure-4B Baseline Verifier（Experiment 1）

```
Verifier = Qwen3-4B-Thinking-2507
```

即：

```
Solver = 4B
Verifier = 4B
```

目的是得到一个完全由 4B 模型构成的 Heavy Pipeline baseline。

## 3.3 Strong Verifier（Experiment 2 & 3）

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
