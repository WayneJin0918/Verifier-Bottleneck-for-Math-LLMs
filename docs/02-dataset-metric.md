# 2. 数据集与评测对象

所有核心实验统一使用：

| 项 | 值 |
|----|-----|
| Dataset | AIME 2025 |
| Number of problems | 30 |

## 主 Metric

主指标是结构任务利用率。并行多采样和串行多轮反思都用它来比较，不用单独的准确率。

\[
\mathrm{STU}
= \frac{A \cdot \beta \cdot \rho}{\alpha \cdot \tau}
,\qquad
\tau = \frac{T_{\mathrm{read}}}{1024}.
\]

- \(A\)：AIME exact-answer accuracy，正确题数 / 30
- \(\alpha\)：激活参数占比 \(P_{\mathrm{act}}/P_{\mathrm{tot}}\)，按 solver / verifier 的读入 token 加权
- \(\beta\)：注意力落在与答案相关 token 上的质量占比
- \(\rho\)：读入 token 与答案的相关程度占比
- \(\tau\)：读入长度，相对 1024 token

\(A\) 仍是任务对错。\(\alpha\)、\(\beta\)、\(\rho\) 用来判断这些对错是以什么样的结构代价和 token 利用率换来的。定义与结果表见 [metrics/definitions.md](../metrics/definitions.md)。

## 跨实验可比性约束

以下内容应保持一致：

- 数据集
- solver checkpoint
- generation prompt
- answer extraction
- temperature
- top-p
- generation max length
- Heavy Pipeline search budget
- 最终 AIME evaluator
- \(\mathrm{rel}(t)\) 的标注规则
- \(T_{\mathrm{ref}}=1024\)
