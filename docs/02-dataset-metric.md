# 2. 数据集与评测对象

所有核心实验统一使用：

| 项 | 值 |
|----|-----|
| Dataset | AIME 2025 |
| Number of problems | 30 |

## 主 Metric

最终任务指标为 AIME exact-answer accuracy：

\[
\text{Accuracy} = \frac{\text{正确题数}}{30}.
\]

详见 [metrics/definitions.md](../metrics/definitions.md)。

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
