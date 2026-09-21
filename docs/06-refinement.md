# 6. Refinement 的实验逻辑

Heavy Pipeline 不只做：

```
generate -> verify -> choose
```

还包含后续 refinement。

## 总体逻辑

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

与统一参数的对应关系：

- `n_proofs_to_refine = 1`：每轮选出需要 refinement 的 proof 数量
- `max_rounds = 16`：refinement / 搜索轮次上限
- 每次新候选仍进入 verification + ranking，再更新 pool
