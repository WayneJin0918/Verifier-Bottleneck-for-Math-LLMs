# 1. 实验目标

整个项目围绕 DeepSeekMath-V2 的 Heavy Pipeline / High-Compute Search 展开，核心目标不是单纯追求更高的 AIME 分数，而是分析：

1. 小模型 solver 在大量采样下到底有没有生成正确解的能力；
2. Heavy Pipeline 的瓶颈究竟来自 generation 还是 verification / selection；
3. 将 verifier 从 Qwen3-4B 替换成更强的 DeepSeek-V4-Flash 后，是否能更好地从候选中找出正确解；
4. 在使用强 verifier 的基础上，引入 STOP 风格的中途检查，是否能够用更少计算量达到相同或更高的最终准确率。

## 递进关系

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

## 三个核心研究问题

\[
\boxed{
\text{Generator potential}
\rightarrow
\text{Verifier bottleneck}
\rightarrow
\text{Online verification efficiency}
}
\]
