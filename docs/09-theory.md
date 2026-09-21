# 理论支撑

实验计划回答「测什么」。这里回答「为什么这样测，以及在测到之前哪些结论已经是恒等式或定理」。推导用的就是 STU 的定义，不另换公式。经验部分只负责检验假设是否成立；假设不成立时，定理的结论一并撤回，这一点写进博客，而不是把定理当成拟合曲线。

记号与 [metrics/definitions.md](../metrics/definitions.md) 相同：

\[
\mathrm{STU}
= \frac{A\,\beta\,\rho}{\alpha\,\tau},
\qquad
\tau=\frac{T}{T_{\mathrm{ref}}},
\quad T_{\mathrm{ref}}=1024,
\quad T=T_{\mathrm{read}}.
\]

## 1. 对数分解是恒等式

对正的因子取对数：

\[
\log\mathrm{STU}
= \log A+\log\beta+\log\rho-\log\alpha-\log\tau.
\]

比较两种花法 \(X\) 与 \(Y\)：

\[
\Delta\log\mathrm{STU}
= \Delta\log A+\Delta\log\beta+\Delta\log\rho-\Delta\log\alpha-\Delta\log\tau.
\]

右边五项相加就是左边，没有剩余项。博客里的因子分解图（计划中的图 3）是在展示这个等式，不是在做回归。若某一项的 \(\Delta\log\) 解释了 \(\Delta\log\mathrm{STU}\) 的大部分，正文就写那一项；若五项量级相同，就写「没有单一瓶颈」，不要挑绝对值最大的一项讲故事。

## 2. 准确率排序与 STU 排序何时分叉

\(A_X>A_Y\) 但 \(\mathrm{STU}_X<\mathrm{STU}_Y\)，当且仅当准确率的提高倍数小于利用率的损失倍数：

\[
\frac{A_X}{A_Y}
<
\frac{\beta_Y}{\beta_X}
\cdot
\frac{\rho_Y}{\rho_X}
\cdot
\frac{\alpha_X}{\alpha_Y}
\cdot
\frac{\tau_X}{\tau_Y}.
\]

这是定义的直接重排。它把博客的主张从「我们觉得并行浪费」写成一个可以在每一对格子上判定真伪的不等式。对齐预算的含义也由此来：若强制 \(\tau_X=\tau_Y\) 且同一模型使 \(\alpha_X=\alpha_Y\)，不等式收成

\[
\frac{A_X}{A_Y}
<
\frac{\beta_Y\,\rho_Y}{\beta_X\,\rho_X}.
\]

此时分叉只可能来自注意力和 token–答案相关度。这就是实验计划里「先对齐 \(T\) 或 \(C_{\mathrm{act}}\)，再比较」的原因：不把长度和激活占比先配平，不等式右边会被 \(\tau\) 和 \(\alpha\) 主导，看不出反思是否真的改到了答案上。

## 3. \(\beta/\rho\) 是注意力相对均匀阅读的增益

\(\bar a_t\) 是一次前向在读入 token 上的注意力分布，\(\rho\) 是同一批 token 上 \(\mathrm{rel}(t)\) 的均匀平均。因此

\[
\beta=\sum_t \bar a_t\,\mathrm{rel}(t)=\mathbb{E}_{t\sim\bar a}[\mathrm{rel}(t)],
\qquad
\rho=\mathbb{E}_{t\sim\mathrm{unif}}[\mathrm{rel}(t)].
\]

在 \(\rho>0\) 时，

\[
\frac{\beta}{\rho}
\]

等于「按注意力抽样的相关度」除以「按位置均匀抽样的相关度」。\(\beta/\rho>1\) 表示注意力比从头读到尾更集中在与答案相关的 token 上；\(\beta/\rho<1\) 表示注意力比均匀阅读更差。STU 的分子里已经有 \(\beta\rho=\rho^2(\beta/\rho)\)，所以相关度出现两次：一次是材料里有多少有用 token（\(\rho\)），一次是注意力有没有用上它们（\(\beta/\rho\)）。去掉 \(\beta\) 的公式消融（计划图 5）删掉的就是第二次。

## 4. 激活占比与绝对激活量不是同一个代价

单一模型时 \(\alpha=P_{\mathrm{act}}/P_{\mathrm{tot}}\)，该模型读入 \(T\) 个 token 的绝对激活量为 \(C_{\mathrm{act}}=T\,P_{\mathrm{act}}\)。代入定义：

\[
\alpha\tau
= \frac{T\,P_{\mathrm{act}}}{P_{\mathrm{tot}}\,T_{\mathrm{ref}}}
= \frac{C_{\mathrm{act}}}{P_{\mathrm{tot}}\,T_{\mathrm{ref}}},
\]

\[
\mathrm{STU}
= A\,\beta\,\rho\cdot\frac{P_{\mathrm{tot}}\,T_{\mathrm{ref}}}{C_{\mathrm{act}}}.
\]

因此在**同一个模型**上比较时，\(P_{\mathrm{tot}}\) 是常数，STU 与 \(A\beta\rho/C_{\mathrm{act}}\) 排序相同。在 **4B 与 Flash 之间**比较时，\(P_{\mathrm{tot}}\) 从约 4B 变成约 284B，STU 会额外乘上总参数量之比。Flash 可以在 \(C_{\mathrm{act}}\) 更大的情况下仍得到更高的 STU，只因为分母里是占比而不是绝对激活量。

这条不是实验结论，是公式的代数后果。博客正文必须同时给出 STU 和 \(C_{\mathrm{act}}\)。只报告 STU 时，不能把 Flash 的领先写成「算得更少」。

Pipeline 上有 solver 与 verifier 两个模型时，

\[
\alpha
= \frac{T_s P_{\mathrm{act},s}+T_v P_{\mathrm{act},v}}{T_s P_{\mathrm{tot},s}+T_v P_{\mathrm{tot},v}}.
\]

Heavy Pipeline 第一轮验证约 \(30\times 64\times 64\) 次调用，\(T_v\) 远大于生成的 \(T_s\)。此时

\[
\alpha\to\alpha_v.
\]

4B 自验证给出 \(\alpha\to 1\)；换成 Flash 给出 \(\alpha\to 13/284\approx 0.0458\)，STU 在 \(A,\beta,\rho,\tau\) 都不变时大约变为原来的 \(1/0.0458\approx 21.8\) 倍。所以验证器一换，\(\alpha\) 项就会淹没 \(\beta\) 和 \(\rho\) 的变化。实验计划把 Flash 限制在主图的格子上，并且要求分解 \(\Delta\log\mathrm{STU}\)，就是为了不让这个极限变成整篇博客的结果。

## 5. 独立并行采样：准确率上升时 STU 下降

设每条 proof 独立，以概率 \(p\in(0,1)\) 抽出正确答案，读入代价与条数成正比：\(\tau(n)=c\,n\)，\(c>0\)。生成器上界为

\[
A_{\mathrm{pass}}(n)=1-(1-p)^n.
\]

并设加宽时 \(\beta\)、\(\rho\)、\(\alpha\) 不变。这对应「新样本与旧样本同分布，验证器的注意力和相关度不因池子变大而改变」。记 \(q=1-p\in(0,1)\)，

\[
\mathrm{STU}(n)
= K\cdot\frac{1-q^n}{n},
\qquad
K=\frac{\beta\rho}{\alpha\,c}>0.
\]

**命题.** 在上述假设下，\(A_{\mathrm{pass}}(n)\) 对正整数 \(n\) 严格递增，\(\mathrm{STU}(n)\) 严格递减。因此按准确率，宽度越大越好；按 STU，宽度越小越好。两条排序在每一对 \(n<n'\) 上都分叉。

**证明.** \(A_{\mathrm{pass}}(n+1)-A_{\mathrm{pass}}(n)=p\,q^n>0\)，故准确率严格递增。

对 STU，记 \(f(n)=(1-q^n)/n\)。只要 \(f\) 严格递减即可。该式等价于 \((n+1)(1-q^n)>n(1-q^{n+1})\)，整理得

\[
1-q^n>n(1-q)\,q^n.
\]

令 \(m=1/q>1\)。左边除以 \(q^n\) 后，上式就是 \(m^n-1>n(m-1)\)。因式分解

\[
m^n-1=(m-1)(m^{n-1}+\cdots+1).
\]

括号里有 \(n\) 项，每一项都 \(\ge 1\)，且因为 \(m>1\)，其中 \(m^{n-1}>1\)，所以和严格大于 \(n\)。于是 \(m^n-1>n(m-1)\)，严格成立。故 \(f(n)>f(n+1)\)。证毕。

**推论.** 在线性代价和同分布假设下，STU 没有内部最优宽度，使它最大的并行宽度是 \(n=1\)。Pass@\(n\) 则一直上升，只是增量按 \(q^n\) 衰减。

这个分叉是对生成器上界而言的。选出的准确率 \(A_{\mathrm{sel}}\le A_{\mathrm{pass}}\)，但它的增长倍数可以更大：若 \(n=1\) 时几乎选错、\(n=2\) 时突然选对，\(A_{\mathrm{sel}}(2)/A_{\mathrm{sel}}(1)\) 可以超过 \(2\)，从而在这一步上 STU 上升。因此命题不能自动推广到验证器选出的准确率。能自动推广的只有下面这条，它不再使用独立同分布的具体形式。只要 \(\beta,\rho,\alpha\) 不随 \(n\) 改变且 \(\tau\propto n\)，

\[
\mathrm{STU}(n+1)>\mathrm{STU}(n)
\iff
\frac{A(n+1)}{A(n)}>\frac{n+1}{n}.
\]

Pass@\(n\) 永远不满足右边。选出的准确率只有在「增长倍数超过预算倍数」时才会让 STU 上升。实验 B 同时报告 Pass@\(n\) 和 \(A_{\mathrm{sel}}\)，就是为了把这两种情形分开。若观测到并行加宽使 STU 上升，被否定的是「\(\beta,\rho,\alpha\) 不变且代价线性」，或者是「准确率的增长倍数没有超过预算倍数」。否定的不是 STU 的定义。

## 6. 一轮反思何时优于再抽一条

并行再抽一条，在第 5 节的假设下把代价从 \(T\) 增到约 \(2T\)（\(n\) 从 1 到 2），准确率从 \(p\) 增到 \(1-q^2=p(1+q)\)，\(\beta,\rho\) 不变。STU 按命题下降。

反思不是再抽一条独立样本。设当前轨迹有 \(T\) 个 token、相关度 \(\rho\)，其中无关 token 为 \((1-\rho)T\)。一轮反思：

- 额外读入批评和改写，代价增量为 \(H\)，新的总读入为 \(T'=T+H\)。前缀被保留时，\(H\) 小于一整条新 proof 的长度。
- 无关 token 中有比例 \(\lambda\in[0,1]\) 被改成与答案相关。相关 token 数从 \(\rho T\) 变为 \(\rho T+\lambda(1-\rho)T\)。
- 注意力从 \(\beta\) 变为 \(\beta'\)。

新的相关度为

\[
\rho'
= \frac{\big(\rho+\lambda(1-\rho)\big)\,T}{T+H}.
\]

它高于改写前的 \(\rho\)，当且仅当新建的相关 token 多于额外读入按旧相关度所占的份额：

\[
\lambda(1-\rho)\,T>\rho\,H.
\]

批评很长（\(H\) 大）或几乎没有改对（\(\lambda\) 小）时，反思之后的 \(\rho\) 反而下降。同分布的重采样不提高相关度：新轨迹的相关度仍是 \(\rho\)，池子的平均也仍是 \(\rho\)，只增加长度。因此只要上式成立，反思的相关度就同时高于「不改」和「再抽一条同分布样本」。预算不同，所以和再抽一条比 STU 时仍用第 2 节的完整不等式，不能只比 \(\rho\)。\(\lambda\) 和 \(H\) 不必单独辨识，它们已经进入测到的 \(\rho'\) 和 \(\tau'\)。重采样对照对应 \(\lambda=0\)。这是实验 C 在理论上的位置。

STOP 是把 \(H\) 在前缀处截断。截断减小 \(H\)，使 \(\rho'>\rho\) 更容易成立；若截断时正确答案尚未出现，准确率 \(A\) 下降。第 2 节的不等式决定哪一边更大。过早停止与过晚停止（实验 D）分别对应 \(A\) 的损失和 \(H\) 的浪费，不需要新的指标。

## 7. 写进博客时如何使用

正文可以按这个顺序用，而不必把证明全文贴出：

1. 用第 2 节的不等式说明「准确率更高」和「STU 更高」不是同一句话。
2. 用第 5 节的命题说明：独立、同分布、线性代价的并行加宽，使 Pass@\(n\) 上升、对应的 STU 下降，而且这个 STU 的最优宽度是 \(n=1\)。这不是拟合出来的缩放律。选出的准确率是否也让 STU 下降，由增长倍数是否超过 \((n+1)/n\) 决定。
3. 用第 6 节说明：反思要提高相关度，必须满足 \(\lambda(1-\rho)T>\rho H\)。同分布重采样做不到这一点，它是 \(\lambda=0\) 的对照。STU 的比较仍用第 2 节，因为两者预算不同。
4. 用第 4 节说明 Flash 的 \(\alpha\) 优势在验证 token 占主导时是代数极限，约 22 倍，必须用分解图拆开，不能当作效率结论。

实验若拒绝第 5 节的假设，结论写成假设失败的方式（代价非线性，或 \(\beta,\rho\) 随宽度变化），不改 STU 的定义。
