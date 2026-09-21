More samples are the usual way to spend test time on a hard math problem. Draw another proof, score the pool, keep the best. Accuracy goes up. That is real, and it is not the same fact as the run having used the model on the answer.

We score a run by structural task utilization. Let \(A\) be exact-answer accuracy on the 30 problems of AIME 2025. Let \(\beta\) be the share of attention that lands on tokens the answer depends on, and \(\rho\) the share of tokens read that are about the answer. Let \(\alpha\) be activated parameters over total parameters, weighted by who read the tokens, and let \(\tau=T/1024\) with \(T\) the tokens read. Then

\[
\mathrm{STU}=\frac{A\,\beta\,\rho}{\alpha\,\tau}.
\]

The numerator is the return and the use of the context. The denominator is the structural price per token and the length of the read. A higher score is not a higher accuracy. We report the five factors with the score, because the product does not say which factor moved.

## When the rankings split

Take two procedures \(X\) and \(Y\). Accuracy can prefer \(X\) while STU prefers \(Y\). From the definition, that happens exactly when

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

The gain in accuracy is smaller than the loss in utilization. If the two procedures read the same number of tokens and use the same model, \(\tau\) and \(\alpha\) cancel, and the split can come only from attention and from how much of the text is about the answer. We match those budgets before we compare. Otherwise length, or the activation ratio, decides the inequality by itself.

Taking logs makes the same statement additive:

\[
\Delta\log\mathrm{STU}
=\Delta\log A+\Delta\log\beta+\Delta\log\rho-\Delta\log\alpha-\Delta\log\tau.
\]

The five terms sum to the left-hand side. There is no residual to fit. If they are the same size, there is no single bottleneck to name.

Attention and relevance are not the same average. \(\beta\) is relevance under the attention distribution. \(\rho\) is relevance under a uniform read of the same tokens. Their ratio \(\beta/\rho\) is whether attention beats reading every token equally. The product \(\beta\rho\) therefore counts relevance twice: once for how much useful text was read, and once for whether attention used it.

## Parallel width

Suppose each proof is correct with probability \(p\in(0,1)\), independently of the others, and the tokens read grow in proportion to the number of proofs, \(\tau(n)=cn\). The chance that at least one proof is correct is

\[
A_{\mathrm{pass}}(n)=1-(1-p)^n.
\]

Hold \(\beta\), \(\rho\), and \(\alpha\) fixed. New samples do not change how relevant a typical proof is, and they do not change where attention sits. Write \(q=1-p\) and \(K=\beta\rho/(\alpha c)\). Then

\[
\mathrm{STU}(n)=K\cdot\frac{1-q^n}{n}.
\]

\(A_{\mathrm{pass}}(n)\) is strictly increasing, because each added proof still has a positive chance of being the first correct one. \(\mathrm{STU}(n)\) is strictly decreasing. To see the second claim, set \(m=1/q>1\). The inequality \((1-q^n)/n>(1-q^{n+1})/(n+1)\) rearranges to \(m^n-1>n(m-1)\). The left side factors as \((m-1)\) times a sum of \(n\) terms, each at least 1, and the largest term is strictly greater than 1, so the sum is strictly greater than \(n\).

Under these assumptions the width that maximizes STU is one sample. Pass@\(n\) keeps rising, with increments that shrink by \(q^n\). Accuracy and utilization rank the widths in opposite orders. This is not a curve fit to a compute budget. It is the definition plus independent draws and a linear token cost.

Selected accuracy is a different object. It cannot exceed Pass@\(n\), but its growth ratio can be steeper. A verifier that fails at \(n=1\) and suddenly succeeds at \(n=2\) can raise STU on that step, because STU rises with \(n\) only when

\[
\frac{A(n+1)}{A(n)}>\frac{n+1}{n},
\]

so long as \(\beta\), \(\rho\), and \(\alpha\) stay fixed and \(\tau\) stays proportional to \(n\). Pass@\(n\) never clears that bar. Selected accuracy does only if it jumps faster than the budget. We will report both, so a rise in STU is not mistaken for a failure of the proposition about the ceiling.

If a wider pool raises STU, what failed is an assumption: cost was not linear in the number of proofs, or attention and relevance moved with the pool. We would not edit the definition to remove the rise.

## One round of reflection

Another independent draw is the step from \(n=1\) to \(n=2\). Cost roughly doubles, accuracy moves from \(p\) to \(p(1+q)\), relevance does not change, and STU falls by the proposition above.

Reflection keeps the trajectory. It has \(T\) tokens and relevance \(\rho\), so \((1-\rho)T\) tokens are not about the answer. The critique and the rewrite add \(H\) tokens. A fraction \(\lambda\) of the irrelevant tokens is replaced by tokens the answer depends on. The new relevance is

\[
\rho'=\frac{(\rho+\lambda(1-\rho))\,T}{T+H}.
\]

This is higher than \(\rho\) exactly when \(\lambda(1-\rho)T>\rho H\). The new relevant tokens have to outnumber the slice of the extra read that the old relevance would already have accounted for. A long critique or a rewrite that changes little lowers relevance. The run paid to reread.

An identically distributed resample cannot raise relevance. The new proof is still relevance \(\rho\), and the pool average stays \(\rho\). Only the length grows. So the inequality is also the condition under which reflection is more relevant than drawing again. The budgets still differ, and the STU comparison uses the ranking inequality above, not \(\rho\) alone. Resampling is the control with \(\lambda=0\). We do not need to estimate \(\lambda\) and \(H\) as separate parameters. They are already inside the measured relevance and the measured length.

Stopping at a prefix is a cut in \(H\). A shorter extra read makes the relevance inequality easier. If the answer is not in the prefix yet, accuracy falls, and the ranking inequality decides which effect wins. An early stop and a late stop are that loss and that wasted read.

## What the activation ratio multiplies

For one model, \(\alpha=P_{\mathrm{act}}/P_{\mathrm{tot}}\) and the absolute activation is \(C_{\mathrm{act}}=T\,P_{\mathrm{act}}\). Substitution gives

\[
\mathrm{STU}=A\,\beta\,\rho\cdot\frac{P_{\mathrm{tot}}\,T_{\mathrm{ref}}}{C_{\mathrm{act}}}.
\]

On a single model the total parameter count is a constant, and STU ranks runs with \(A\beta\rho/C_{\mathrm{act}}\). Between models it does not. The dense 4B verifier has \(\alpha=1\). DeepSeek-V4-Flash activates about 13B of about 284B parameters, so \(\alpha\approx 0.0458\), and it still activates more parameters in absolute terms than the 4B model. STU can prefer Flash while \(C_{\mathrm{act}}\) is larger, because the denominator is a fraction of a large model.

In the pipeline the ratio is weighted by tokens read. The first verification round of the Heavy Pipeline setting is \(30\times 64\times 64\) calls, so verifier tokens dominate generation tokens and \(\alpha\) collapses to the verifier's own ratio. Swapping the 4B verifier for Flash, with \(A\), \(\beta\), \(\rho\), and \(\tau\) held fixed, multiplies STU by about 21.8. That factor will swamp a real change in attention unless we decompose \(\Delta\log\mathrm{STU}\). We will report \(C_{\mathrm{act}}\) beside STU. A lead on STU alone is not less compute.

## What we still measure

The proposition tells us what independent parallel sampling must do. The measurements ask where the assumptions break. The solver stays Qwen3-4B-Thinking-2507. Temperature is 1.0 and top-p is 0.95. The verifier is either the same 4B model or Flash, and only one of those changes at a time.

We need the generator ceiling, Pass@\(n\), on the samples we already draw, because selection cannot be the bottleneck if the correct answer was never written. We need a majority vote on the same proofs, because a gain that a vote can match is not a gain from verification. We need reflection against resampling at a matched token budget, because serial depth that only discards and redraws is parallel sampling in sequence. We need the STOP prefixes at 4k, 8k, 12k, and 16k on those reflection traces, counted as early or late relative to whether the answer is already in the prefix. Flash is run on the cells of that comparison, not on the whole grid. The same runs are ranked again by \(A\), by \(A/\tau\), by the score with attention removed, and by full STU. If those rankings agree, the note says STU added nothing here.

The Heavy Pipeline cell, 64 parallel proofs and up to 16 rounds of rewriting one of them, is one corner of this grid. It is not the result.
