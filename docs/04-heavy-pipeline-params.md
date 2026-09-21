# 4. Heavy Pipeline 统一核心参数

目前锁定的 Heavy Pipeline 参数如下。它们是并行 × 串行网格里参考格 \((n=64,\ r\le 16)\) 的搜索设置，不是唯一要跑的一点。扫宽度或深度时，除了正在变化的 \(n\) 或 \(r\)，下表保持不变。网格见 [07-experiments.md](07-experiments.md)。

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

## Experiment 2 控制原则

**只替换 verifier，不改变 Heavy Pipeline 的搜索参数。**

这样才能把：

```
4B self-verifier
vs
DeepSeek-V4-Flash verifier
```

的效果单独隔离出来。
