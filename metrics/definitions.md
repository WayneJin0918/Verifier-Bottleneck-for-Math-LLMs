# Metric 形式化定义

只看 AIME 准确率，或只看 verification score，回答不了「这次计算在任务上是否用得有效」。准确率是结果；模型有没有把参数、注意力和读入的 token 用在答案上，才是效率。

主指标是 **结构任务利用率（Structural Task Utilization, STU）**。它由四项组成，方向不同，不能都当成越大越好直接相乘：

| 因子 | 记号 | 含义 | 进入 STU 的方式 |
|------|------|------|-----------------|
| 任务准确率 | \(A\) | 最终答案对不对 | 分子，越大越好 |
| 注意力利用率 | \(\beta\) | 注意力是否落在与答案相关的 token 上 | 分子，越大越好 |
| 读取 token–答案相关占比 | \(\rho\) | 读进来的 token 里，有多少和答案相关 | 分子，越大越好 |
| 激活参数占比 | \(\alpha\) | 每个 token 实际唤醒的参数占模型总参数的比例 | 分母，占比越低，同样准确率的结构代价越小 |

读入长度单独归一化，避免只靠少读 token 把分数做高而不被看见。

---

## 1. 主指标

\[
\boxed{
\mathrm{STU}
= \frac{A \cdot \beta \cdot \rho}{\alpha \cdot \tau}
,\qquad
\tau = \frac{T_{\mathrm{read}}}{T_{\mathrm{ref}}}
}
\]

\(T_{\mathrm{ref}} = 1024\)，固定不变。STU 无量纲，越高越好：更常做对，注意力更集中在与答案相关的 token 上，读入内容里与答案相关的占比更高，每个 token 唤醒的参数占比更低，而且没有无谓地读更长的上下文。

比较任何两组实验时，除 STU 外必须同时报告 \((A, \alpha, \beta, \rho, T_{\mathrm{read}})\)。只报乘除之后的一个数，看不出分是从准确率来的，还是从更稀疏的激活、更准的注意力或更短的上下文来的。

### 1.1 准确率 \(A\)

\[
A = \frac{\#\{\text{AIME 2025 上 exact-answer 正确的题}\}}{30}.
\]

答案判定与统一 AIME evaluator 一致。\(A\) 是任务回报，不是效率本身。

### 1.2 激活参数占比 \(\alpha\)

对单个模型：

\[
\alpha_m = \frac{P_{\mathrm{act}}(m)}{P_{\mathrm{tot}}(m)}.
\]

| 模型 | 结构 | \(P_{\mathrm{tot}}\) | \(P_{\mathrm{act}}\) | \(\alpha_m\) |
|------|------|----------------------|----------------------|--------------|
| Qwen3-4B-Thinking-2507 | Dense | \(\approx 4\mathrm{B}\) | \(\approx 4\mathrm{B}\) | \(1\) |
| DeepSeek-V4-Flash | MoE | \(\approx 284\mathrm{B}\) | \(\approx 13\mathrm{B}\) | \(\approx 13/284 \approx 0.0458\) |

Pipeline 里 solver 和 verifier 不是同一个模型，按各自读入 token 数加权，而不是把两个 \(\alpha\) 简单平均：

\[
\alpha
= \frac{\sum_m T_m \, P_{\mathrm{act},m}}{\sum_m T_m \, P_{\mathrm{tot},m}}.
\]

\(T_m\) 是角色 \(m\) 在一道题上读入的 token 数（该角色全部调用之和），再对 30 题取平均。Dense 的 4B 自验证 \(\alpha = 1\)。换成 Flash 之后，\(\alpha\) 下降只来自 verifier 那一部分；solver 仍是 4B。若 verifier 的读入 token 占主导，\(\alpha\) 会靠近 \(0.0458\)，而不是 \(1\) 和 \(0.0458\) 的算术平均。

\(\alpha\) 放在分母，是因为占比衡量的是结构代价：每个 token 要唤醒模型的多大一块。它不是 FLOPs。Flash 的 \(\alpha\) 远小于 4B，但绝对激活参数约 13B，仍大于 4B。因此结果表里另报绝对激活参数量

\[
C_{\mathrm{act}} = \sum_m T_m \, P_{\mathrm{act},m},
\]

避免把「占比更低」说成「算得更少」。

### 1.3 注意力利用率 \(\beta\)

对一次前向，把各层、各头、各 query 的注意力对上下文 token 取平均，得到读入 token 上的分布 \(\bar{a}_t\)（\(\sum_t \bar{a}_t = 1\)）：

\[
\bar{a}_t
= \frac{1}{LHQ}\sum_{\ell,h,q} A^{(\ell,h)}_{q,t}.
\]

\[
\beta_{\mathrm{call}} = \sum_t \bar{a}_t \, \mathrm{rel}(t)
\in [0,1].
\]

\(\beta\) 高，表示注意力质量落在与答案相关的 token 上。注意力很尖、但尖在无关 token 上时，\(\beta\) 仍然低。

注意力熵只作诊断，不进入 STU：

\[
H = -\sum_t \bar{a}_t \log \bar{a}_t.
\]

\(H\) 低只说明注意力集中，不说明集中对了地方。Pipeline 级 \(\beta\) 与 \(\alpha\) 一样，按 \(T_m\) 加权：

\[
\beta = \frac{\sum_m T_m \beta_m}{\sum_m T_m}.
\]

### 1.4 读取 token 与答案的相关占比 \(\rho\)

\[
\rho = \frac{1}{T_{\mathrm{read}}}\sum_t \mathrm{rel}(t)
\in [0,1],
\qquad
T_{\mathrm{read}} = \sum_m T_m.
\]

\(\rho\) 不看注意力，只看读入内容本身有多少和答案相关。因此它和 \(\beta\) 分开：

| \(\rho\) | \(\beta\) | 含义 |
|----------|-----------|------|
| 高 | 高 | 读入的内容大多有用，注意力也落在这些内容上 |
| 高 | 低 | 上下文里有答案所需信息，但注意力没用上 |
| 低 | 高 | 大部分 token 与答案无关，注意力只抓住了少数相关 token |
| 低 | 低 | 既读了很多无关内容，注意力也没有对准 |

\(\mathrm{rel}(t)\in[0,1]\)，只给对最终答案有贡献的 token：

- 题面中的条件、约束、所求量
- 推出该答案所必需的中间量或关系
- 答案本身

放弃的分支、重复转述、与答案无关的套话，\(\mathrm{rel}\) 低。标注规则一旦改变，STU 不能横向比较。

### 1.5 读入长度 \(\tau\)

\[
\tau = T_{\mathrm{read}} / 1024.
\]

STOP 的 4k / 8k / 12k / 16k 前缀会改变 \(T_{\mathrm{read}}\)。若中途停下后 \(A\) 不降、\(\rho\) 上升，STU 会高于把整段推理读完的 Heavy Pipeline。这是准确率曲线上看不到的部分。

---

## 3. 在并行 / 串行网格上怎么用

STU 用来比较 test-time scaling 的两种花法，而不是替代网格里的选择规则。格子内部仍然用 verification score 选 proof。格子之间在 \(T_{\mathrm{read}}\) 或 \(C_{\mathrm{act}}\) 接近时比较 STU 及其分解。协议、对齐方式和否证条件见 [docs/07-experiments.md](../docs/07-experiments.md)。

纯加并行宽度时，预期 \(A\) 上升的同时 \(\rho\) 下降、\(\tau\) 上升。纯加串行反思时，只有 \(\beta\) 和 \(\rho\) 上升，STU 才说明反思用在了答案上。同一 \((n,r)\) 只更换 verifier 时，\(\alpha\) 与 verifier 的 \(\beta\) 分开看，不能把 Flash 更低的激活占比直接当成更少的计算。

---

## 4. Verification score 不是任务指标

Verifier 的 rating 仍是 \(r_i\in\{0, 0.5, 1\}\)。同一 proof 的 64 次评分

\[
s(p) = \frac{1}{64}\sum_{i=1}^{64} r_i
\]

只用于候选排序。曾观测到 \(s = 0.9921875 = (63\times 1 + 1\times 0.5)/64\)，与这个平均一致。

\(s(p)\) 不进入 STU，也不作为最终答案。最终对错只看抽出的答案是否通过 AIME evaluator。

---

## 5. 结果记在网格上

\(T_{\mathrm{read}}\)、\(C_{\mathrm{act}}\) 均为每题平均。\(\alpha\)、\(\beta\)、\(\rho\) 为 token 加权平均。每一格 \((n,r)\) 的表见 [docs/07-experiments.md](../docs/07-experiments.md)。Pure-4B 与 Flash verifier 各填一份，不要把两张表合成一行。

### 可比性约束

下列任一项变化后，不得直接比较 STU 或 \(A\)：

- 数据集与 AIME evaluator
- solver checkpoint、generation prompt、answer extraction
- temperature、top-p、generation max length、Heavy Pipeline search budget
- \(\mathrm{rel}(t)\) 的标注规则
- \(T_{\mathrm{ref}}\)（固定为 1024）
