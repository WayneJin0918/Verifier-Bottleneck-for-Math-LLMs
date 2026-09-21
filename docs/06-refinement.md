# 6. 串行反思的一轮

串行 test-time scaling 的一轮不是重新采样，而是对已经选中的 proof 做一次反思再改写。Heavy Pipeline 的 refinement 就是这个步骤；重复 \(r\) 次即深度轴。与纯并行的差别见 [07-experiments.md](07-experiments.md)。

一轮的内部顺序：

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
