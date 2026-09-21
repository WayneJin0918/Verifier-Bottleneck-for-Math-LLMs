# 4. Heavy Pipeline 统一核心参数

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

## Experiment 2 控制原则

**只替换 verifier，不改变 Heavy Pipeline 的搜索参数。**

这样才能把：

```
4B self-verifier
vs
DeepSeek-V4-Flash verifier
```

的效果单独隔离出来。
