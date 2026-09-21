# 1. 实验目标

要验证的不是「多采样能不能把 AIME 做高」，而是：test-time scaling 的效率应不应该用结构任务利用率来衡量。

\[
\mathrm{STU}=\frac{A\cdot\beta\cdot\rho}{\alpha\cdot\tau}
\]

\(A\) 是准确率，\(\beta\) 是注意力有没有落在与答案相关的 token 上，\(\rho\) 是读入 token 与答案的相关占比，\(\alpha\) 是激活参数占比，\(\tau\) 是相对 1024 的读入长度。定义见 [metrics/definitions.md](../metrics/definitions.md)。

只加准确率，区分不开两种花法：

- **并行**：再独立生成一条证明。多出来的往往是一整段与答案无关的轨迹，\(\tau\) 上升、\(\rho\) 下降，准确率仍可能上升。
- **串行反思**：对着同一条轨迹验证、指出问题、再改写，重复多轮。有效的一轮应让注意力移到出错的那一步（\(\beta\) 上升），并换掉与答案无关的 token（\(\rho\) 上升）。STOP 的 4k / 8k / 12k / 16k 前缀检查是串行过程里的提前截断，不是第三套实验。

因此实验是一张宽度 × 深度的表，而不是三条互不相关的流水线。Heavy Pipeline 的 \(n=64\)、最多 16 轮修正，只是这张表里的一个格子。协议见 [07-experiments.md](07-experiments.md)。

## 三个要分开的问题

\[
\boxed{
\text{Parallel width}
\rightarrow
\text{Serial reflection depth}
\rightarrow
\text{Verifier activation}
}
\]

| 问题 | 怎么动 | 看 STU 的哪一项 |
|------|--------|-----------------|
| 小模型在多采样下有没有正确解 | 只加并行宽度 \(n\) | \(A\) 是否上升，以及上升时 \(\rho\) 是否被新轨迹稀释 |
| 反思是在改写无关 token，还是在空转 | 只加串行轮数 \(r\)，或在轮内按前缀截断 | \(\beta\)、\(\rho\) 是否上升，\(\tau\) 是否比再开一批并行更小 |
| 更强的 verifier 是结构上更省，还是只是更会打分 | 同一 \((n,r)\)，把 verifier 从 4B（\(\alpha=1\)）换成 Flash（\(\alpha\approx 0.0458\)） | \(A\) 与 \(\beta\) 是否一起上升；\(\alpha\) 下降不能单独当成算得更少 |
