## Introduction

More samples are the usual way to spend test time on a hard math problem. A chain-of-thought trace already spends that budget inside one sample [@wei2022] [@kojima2022]. Further test-time compute is then either a longer trace [@openai2024] [@deepseekr1] [@muennighoff2025], a search over revisions [@snell2024] [@yao2023], or another independent sample whose answers are aggregated by a vote [@wang2023]. Accuracy goes up. That is real, and it is not the same fact as the run having used the model on the answer.

We score a run by structural task utilization. Let \(A\) be exact-answer accuracy on the set being scored. Let \(\beta\) be the share of attention that lands on tokens the answer depends on, and \(\rho\) the share of tokens read that are about the answer. Let \(\alpha\) be activated parameters over total parameters, weighted by who read the tokens, and let \(\tau=T/1024\) with \(T\) the tokens read. Then

\[
\mathrm{STU}=\frac{A\,\beta\,\rho}{\alpha\,\tau}.
\]

The numerator is the return and the use of the context. The denominator is the structural price per token and the length of the read. A higher score is not a higher accuracy. We report the five factors with the score, because the product does not say which factor moved.

```diagram
factors
```

On AIME 2025 [@aime], one finished sample from Qwen3-4B-Thinking-2507 [@qwen3think] scores 25 of 30. The published figure for this checkpoint is 81.3. This run is one seed, and one problem is 3.3 points, so the two figures sit side by side. A majority vote over eight independent samples scores 27 of 30 [@wang2023]. Tokens per problem scale by 8.15. From one sample to eight,

\[
\Delta\log(A/\tau)=\Delta\log A-\Delta\log\tau=0.077-2.098=-2.021.
\]

Accuracy is the small term. One sample already scores above one half. With \(\beta\), \(\rho\), and \(\alpha\) held fixed, and with tokens growing in proportion to the width, every wider pool has lower utilization than that sample. The sections below derive that ceiling and then measure what the extra samples buy. The measured score is \(A/\tau\).

## Related work

Test-time scaling treats inference as a second compute axis. Snell et al. compare search against a process reward model with a revision that updates the model's own distribution, and they allocate that compute by the difficulty of the prompt [@snell2024]. OpenAI's o1 and DeepSeek-R1 spend the extra compute inside one thinking trace [@openai2024] [@deepseekr1]. s1 forces the trace to continue, or cuts it, with a thinking budget [@muennighoff2025]. Qwen3 puts a thinking mode and a thinking budget in the same model family [@qwen3]. Those methods change the length of one read. This note asks a different question: once a trace can finish, does another independent sample raise accuracy faster than it raises the tokens read.

Parallel samples are the other axis. Self-consistency draws several chain-of-thought answers and keeps the majority [@wang2023]. Pass@\(k\) is the coverage of that pool, the chance that at least one sample is correct [@chen2021]. Brown et al. show that coverage keeps rising over orders of magnitude in the number of samples, while majority vote and reward models plateau [@brown2024]. The proposition in the next section is the utilization counterpart. Under a linear token cost and fixed \(\beta\), \(\rho\), and \(\alpha\), structural task utilization falls while Pass@\(n\) rises. The AIME vote, from 25 of 30 to 27 of 30 while \(A/\tau\) falls by a factor of about 7.5, is that split on one checkpoint.

Verifiers are the usual way to pick one proof from the pool. Cobbe et al. train an outcome verifier on GSM8K [@cobbe2021]. Uesato et al. and Lightman et al. compare outcome supervision with supervision on the steps [@uesato2022] [@lightman2024]. Math-Shepherd trains a step-level reward without new human labels [@mathshepherd]. DeepSeekMath trains mathematical reasoning with a verifier signal in the loop [@deepseekmath]. On our medium band the ratings barely separate correct solutions from incorrect ones, and the selected answer loses to the vote. That is a small pool, not the hundreds of samples in Brown et al., but the direction is the same: a learned score does not automatically recover coverage.

Serial reflection keeps the trajectory. Self-Refine and Reflexion add a critique and a rewrite [@madaan2023] [@shinn2023]. Training a model to self-correct is a separate objective from prompting it to try again [@welleck2023]. Huang et al. find that, without an external check, a second pass does not reliably correct the first [@huang2024]. Our matched-budget comparison is that experiment at eight medium problems: one critique and one rewrite against enough later samples to match the tokens. The accuracies tie. We do not measure \(\rho\), so the comparison is accuracy at a matched read, not an estimate of how much of the critique was about the answer.

The sets are the standard integer-answer collections. GSM8K is grade-school word problems [@cobbe2021]. MATH is competition problems labeled by level [@hendrycks2021]. Minerva showed that a language model trained for quantitative reasoning can attempt that style of problem [@lewkowycz2022]. AIME is the invitational contest [@aime]. The solver and the verifier are the same dense 4B thinking checkpoint [@qwen3think]. DeepSeek-V3 is the public contrast for the activation ratio: it activates 37B of 671B parameters [@deepseekv3]. This note does not run that model. It fixes \(\alpha=1\) and varies the read.

## Structural task utilization

The comparisons in this section hold \(\beta\), \(\rho\), and \(\alpha\) fixed unless a paragraph says otherwise. Attention is the distribution over tokens in the trace [@vaswani2017]. \(\beta\) is that distribution applied to relevance. \(\rho\) is the same relevance read uniformly. Neither one is measured below.

### When the rankings split

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

The gain in accuracy is smaller than the product of the other four ratios. When the two procedures use the same model, \(\alpha\) cancels. When they also read the same number of tokens, \(\tau\) cancels, and the split can come only from attention and from how much of the text is about the answer. The reflection comparison is the one that matches the read. The width comparison leaves the read free, so that length is the term the inequality exposes.

```diagram
split
```

Taking logs makes the same statement additive:

\[
\Delta\log\mathrm{STU}
=\Delta\log A+\Delta\log\beta+\Delta\log\rho-\Delta\log\alpha-\Delta\log\tau.
\]

The five terms sum to the left-hand side. There is no residual to fit. If they are the same size, there is no single bottleneck to name.

Attention and relevance are not the same average. \(\beta\) is relevance under the attention distribution. \(\rho\) is relevance under a uniform read of the same tokens. Their ratio \(\beta/\rho\) is whether attention beats reading every token equally. The product \(\beta\rho\) therefore counts relevance twice: once for how much useful text was read, and once for whether attention used it.

### Parallel width

Suppose each proof is correct with probability \(p\in(0,1)\), independently of the others, and the tokens read grow in proportion to the number of proofs, \(\tau(n)=cn\). The chance that at least one proof is correct is the coverage of the pool [@chen2021] [@brown2024]:

\[
A_{\mathrm{pass}}(n)=1-(1-p)^n.
\]

Hold \(\beta\), \(\rho\), and \(\alpha\) fixed. New samples do not change how relevant a typical proof is, and they do not change where attention sits. Write \(q=1-p\) and \(K=\beta\rho/(\alpha c)\). Then

\[
\mathrm{STU}(n)=K\cdot\frac{1-q^n}{n}.
\]

\(A_{\mathrm{pass}}(n)\) is strictly increasing, because each added proof still has a positive chance of being the first correct one. \(\mathrm{STU}(n)\) is strictly decreasing. Set \(m=1/q>1\). Cross-multiplying the neighboring widths and dividing by \(m-1\) leaves a factor of \(m\) on the left:

\[
\begin{aligned}
\frac{1-q^{n}}{n}
&>
\frac{1-q^{n+1}}{n+1}
\\
&\Longleftrightarrow
m(m^{n}-1)
>
n(m-1)
\\
&\Longleftrightarrow
\sum_{k=1}^{n} m^{k}
>
n.
\end{aligned}
\]

The sum has \(n\) terms. Each term \(m^{k}\) is strictly greater than 1, so the sum is strictly greater than \(n\).

```diagram
width
```

```chart
proposition
```

Under these assumptions the width that maximizes STU is one sample. Pass@\(n\) keeps rising, with increments that shrink by \(q^n\). Accuracy and utilization rank the widths in opposite orders. This is not a curve fit to a compute budget. It is the definition plus independent draws and a linear token cost.

Selected accuracy is a different object. It cannot exceed Pass@\(n\), but its growth ratio can be steeper. A verifier that fails at \(n=1\) and suddenly succeeds at \(n=2\) can raise STU on that step, because STU rises with \(n\) only when

\[
\frac{A(n+1)}{A(n)}>\frac{n+1}{n},
\]

so long as \(\beta\), \(\rho\), and \(\alpha\) stay fixed and \(\tau\) stays proportional to \(n\). Pass@\(n\) never clears that bar. Selected accuracy does only if it jumps faster than the budget. We report both, so a rise in utilization is not mistaken for a failure of the proposition about the ceiling.

The same inequality has a ceiling that does not depend on the selector. Because \(A(n)\le 1\),

\[
\frac{A(n)}{A(1)}\le\frac{1}{A(1)}.
\]

If \(A(1)\ge 1/2\) and \(n\ge 2\), the right-hand side is at most 2, and 2 is at most \(n\). The ratio cannot exceed the token bar. A pool wider than one sample then cannot raise STU, including a pool that scores every problem. The easy band, the medium band, and the full AIME run all start at or above one half. On those sets the utilization ranking between one sample and any wider linear-cost pool is fixed before the wider pool is scored.

If a wider pool raises STU, what failed is an assumption: cost was not linear in the number of proofs, or attention and relevance moved with the pool. We would not edit the definition to remove the rise.

### One round of reflection

Another independent draw is the step from \(n=1\) to \(n=2\). Cost roughly doubles, accuracy moves from \(p\) to \(p(1+q)\), relevance does not change, and STU falls by the proposition above.

Reflection keeps the trajectory. It has \(T\) tokens and relevance \(\rho\), so \((1-\rho)T\) tokens are not about the answer. The critique and the rewrite add \(H\) tokens. A fraction \(\lambda\) of the irrelevant tokens is replaced by tokens the answer depends on. The new relevance is

\[
\rho'=\frac{(\rho+\lambda(1-\rho))\,T}{T+H}.
\]

This is higher than \(\rho\) exactly when \(\lambda(1-\rho)T>\rho H\). The new relevant tokens have to outnumber the slice of the extra read that the old relevance would already have accounted for. A long critique or a rewrite that changes little lowers relevance. The run paid to reread.

An identically distributed resample cannot raise relevance. The new proof is still relevance \(\rho\), and the pool average stays \(\rho\). Only the length grows. The inequality above is the condition under which reflection would be more relevant than drawing again. This note does not measure \(\rho\), so it does not estimate \(\lambda\). The comparison we run holds the number of tokens fixed and scores accuracy.

```diagram
reflect
```

Stopping at a prefix is a cut in \(H\). A shorter extra read makes the relevance inequality easier. If the answer is not in the prefix yet, accuracy falls, and the ranking inequality decides which effect wins. An early stop and a late stop are that loss and that wasted read.

### What the activation ratio multiplies

For one model, \(\alpha=P_{\mathrm{act}}/P_{\mathrm{tot}}\) and the absolute activation is \(C_{\mathrm{act}}=T\,P_{\mathrm{act}}\). Substitution gives

\[
\mathrm{STU}=A\,\beta\,\rho\cdot\frac{P_{\mathrm{tot}}\,T_{\mathrm{ref}}}{C_{\mathrm{act}}}.
\]

On a single model the total parameter count is a constant, and STU ranks runs with \(A\beta\rho/C_{\mathrm{act}}\). Between models it does not. The dense 4B model has \(\alpha=1\) [@qwen3]. DeepSeek-V3 activates 37B of 671B parameters [@deepseekv3]. DeepSeek-V4-Flash activates about 13B of about 284B parameters, so \(\alpha\approx 0.0458\), and it still activates more parameters in absolute terms than the 4B model. STU can prefer Flash while \(C_{\mathrm{act}}\) is larger, because the denominator is a fraction of a large model. This note does not run that comparison.

## Experiments

One dense model, two budgets that are not matched across widths, and one comparison that is matched. \(\beta\) and \(\rho\) are not measured. The score in every table is \(A/\tau\).

```diagram
pipeline
```

### What we ran

The model is Qwen3-4B-Thinking-2507, dense, so \(\alpha=1\). The short checks use temperature 1.0, top-p 0.95, and seed 1234. The AIME run uses the model card's contest sampler: temperature 0.6, top-p 0.95, top-k 20, and seed 1234. Eight GPUs each serve one copy. \(T\) is prompt tokens plus completion tokens on the solutions. Verifier tokens are not in \(\tau\).

We did not measure \(\beta\) or \(\rho\) on these pools. With those two factors held fixed, STU and \(A/\tau\) rank procedures the same way. The numbers below are \(A/\tau\). They are not full STU.

The width check uses two bands of 12 problems, each with one pool of 16 samples, and reads \(n=1,2,4,8,16\) from that pool. Token budgets are not matched across those widths. The easy band is GSM8K items whose first sample boxed the correct integer under 2048 tokens [@cobbe2021]. The medium band is MATH items whose first sample hit a 4096-token cap and a later sample in the same pool boxed the gold answer [@hendrycks2021]. That entry rule makes Pass at the full pool equal to 1. The medium curve records when a prefix of the pool first hits, and what the hit costs. Each easy or medium solution in the pool is capped at 4096 new tokens. Four ratings per solution, on \(\{0,0.5,1\}\), rank proofs for a selected answer. The rating does not enter \(A/\tau\).

A separate generation budget, on the easy band only, caps a fresh sample at 128, 256, 512, or 1024 tokens. Reflection is one critique, allowed 2048 tokens, and one rewrite on eight medium problems, compared with enough later samples from the same pool to match the tokens of that rewrite. That is the matched-budget comparison. The final comparison is AIME 2025, all 30 problems, at the model card's contest length of 81920 new tokens, temperature 0.6, top-p 0.95, and top-k 20. The baseline is one sample. The comparison is a majority vote over 8.

### A short budget

On the twelve easy problems, a fresh sample at 128 tokens is correct on 0 of 12, and so is a sample at 256. At 512 tokens, 5 of 12 are correct. At 1024, all 12 are correct, and the traces stop early: mean tokens read are 198, 326, 554, and 613. \(A/\tau\) is 0, 0, 0.770, and 1.671.

From 512 to 1024, accuracy multiplies by 2.40 and tokens multiply by 1.11, so \(A/\tau\) rises. The rise does not contradict the width proposition. That proposition needs tokens to grow with the number of samples. Here the allowance grew and the finished traces did not spend it. Once the budget is long enough for the box, the easy-band \(A/\tau\) is 1.67, the same value as one unrestricted sample, and the width table takes over from there.

```chart
budget
```

### Width

On the easy band every width is correct on 12 of 12 problems, and the vote agrees. Tokens per problem are 618, 1246, 2448, 4887, and 9808. \(A/\tau\) is 1.658, 0.822, 0.418, 0.210, and 0.104. Accuracy stays at 1, tokens scale with \(n\), and \(A/\tau\) falls as \(1/n\).

On the medium band the vote matches Pass@\(n\) at every width: 6, 8, 10, 12, and 12 out of 12. The last of these is the entry rule. Tokens per problem are 3771, 7402, 14468, 29483, and 58728. \(A/\tau\) is 0.136, 0.092, 0.059, 0.035, and 0.017. Each doubling multiplies accuracy by 1.33, 1.25, 1.20, and 1.00. The bar at a doubling is 2. None of the steps clear it, so \(A/\tau\) falls at every step. One sample scores 6 of 12. From there a perfect pool can multiply accuracy by at most 2. The pool is already perfect at \(n=8\), and the step to \(n=16\) only doubles the read. Utilization falls from 0.136 to 0.017.

The verifier's selected answer on the medium band is 6, 8, and 11 out of 12 at \(n=1,4,16\). The growth ratios are 1.33 and 1.38, against bars of 4. Selection stays under Pass@\(n\) and does not clear the bar either.

The ratings themselves barely separate correct solutions from incorrect ones. Across 384 solutions the mean rating is 0.864 on correct solutions and 0.812 on incorrect ones. Four solutions score below 0.25, and none of them is correct. Sixty-one score from 0.25 up to 0.75, and 65.6% of those are correct. The other 319 score at least 0.75, and 74.3% of those are correct. The verifier almost always assigns a high score. That is why its selection loses to the vote. Outcome and process verifiers are the usual selectors [@cobbe2021] [@uesato2022] [@lightman2024]. Here the score does not recover the coverage of the pool. Forty-five of 1536 individual ratings were missing.

Bootstrap over the 12 problems, 2000 resamples, seed 1234, puts the easy \(A/\tau\) at \(n=1\) in 1.52–1.85 and at \(n=16\) in 0.098–0.112. The medium intervals are 0.065–0.210 and 0.017–0.019. The \(n=1\) and \(n=16\) intervals do not overlap in either band.

```chart
width
```

### Where the answer is written

On the 192 easy traces that contain the correct box, the box begins at a median of 99.2% of the text. The tail after it has median length 0.2% of the text. Cuts at 25%, 50%, and 75% of the characters contain the correct box in 0 of 192 traces. The full text contains it in all 192.

On the 85 medium traces, out of 192, that contain the correct box, the box begins at a median of 99.8% of the characters. The earliest begins at 85.4%. The median tail is 0.06% of the text, and the longest tenth of those tails is 5.3%. Cuts at 25%, 50%, and 75% contain the correct box in 0 of 192 traces. The full text contains it in 85 of 192. An early stop drops the answer. The tail after the box is short.

The same measurement on the 202 correct AIME traces, at the contest length, puts the box at a median of 99.97% of the characters. The answer is the last thing the trace writes. A prefix cut still drops it.

Asking the model, on eight rewrites, whether a 25% prefix or a 75% prefix should stop, produced CONTINUE on all 16 prefixes, including the eight late prefixes that already contained the gold integer. The position of the box is the measurement. The CONTINUE reply is not evidence about when to stop.

### Reflection at a matched budget

A short critique, capped at 512 tokens, left the rewrite correct on 8 of 8 problems and a token-matched bundle of later samples correct on 7 of 8. That critique usually ended inside the thinking trace.

Allowing the critique 2048 tokens, four of the eight critiques stop and say they find no serious mistake. The other four still hit the cap inside the thinking trace. One of those four does name a concrete confusion before the cap. The rewrites are then correct on 7 of 8 problems. Matching the tokens with later samples from the same pool is also 7 of 8. The problem the rewrite misses, the matched samples solve. The problem the matched samples miss, the rewrite solves. At a matched read, reflection does not raise accuracy [@huang2024] [@madaan2023] [@shinn2023]. We still do not have a labeled \(\rho\), so this is an accuracy comparison, not a measurement of \(\lambda\). Reflection is not the procedure we take to AIME.

### AIME 2025

The short cap is a different experiment. At 10240 new tokens and temperature 1.0, a vote over 16 samples scored 7 of 30. Of the 480 traces, 426 hit the cap before they finished.

The contest run uses temperature 0.6, top-p 0.95, top-k 20, and 81920 new tokens. The prompt asks for a step-by-step solution and a boxed integer. One pool of eight samples is read at every width from 1 to 8. All 240 traces stopped. The longest completion is 54770 tokens. The published AIME25 number for this checkpoint is 81.3.

| \(n\) | Pass | Vote | Tokens per problem | \(A/\tau\) | Accuracy ratio | Bar |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 25 | 25 | 22247 | 0.0384 | 1.00 | 1 |
| 2 | 26 | 24 | 43533 | 0.0188 | 0.96 | 2 |
| 3 | 26 | 25 | 65489 | 0.0130 | 1.00 | 3 |
| 4 | 26 | 26 | 88859 | 0.0100 | 1.04 | 4 |
| 5 | 26 | 26 | 112115 | 0.0079 | 1.04 | 5 |
| 6 | 27 | 26 | 134349 | 0.0066 | 1.04 | 6 |
| 7 | 27 | 26 | 157533 | 0.0056 | 1.04 | 7 |
| 8 | 27 | 27 | 181335 | 0.0051 | 1.08 | 8 |

One sample scores 83.3. The vote at eight scores 90.0. The accuracy ratio from one to eight is 1.08, and a perfect pool would reach at most \(30/25=1.20\). The token bar is 8. Both the measured vote and the accuracy ceiling sit under the bar, so \(A/\tau\) at eight samples is 0.132 times \(A/\tau\) at one sample. The bootstrap intervals, 2000 resamples of the 30 problems, are 0.029–0.049 at \(n=1\) and 0.004–0.006 at \(n=8\).

```chart
aime
```

The eight individual draws score 25, 25, 25, 26, 25, 27, 24, and 25. Their average is 25.25 of 30. The best single draw scores 27, the same number the vote of eight reaches when a tie breaks toward the smaller integer.

Pass@\(n\) is monotone. The vote is not. At \(n=2\) it falls from 25 to 24. Problem 20's first sample is the gold answer 336, and its second sample is 333. The two answers tie, and the tie breaks toward the smaller integer, so the vote leaves the gold. In the same step Pass@2 rises to 26, because problem 10's second sample is the gold 81, while that problem's vote also ties, between 70 and 81, and keeps 70. By \(n=8\), problem 10 has three votes for 81 and the vote is correct. Problem 30 ties 3–3 between 240 and 752, and the smaller integer is the gold, so the vote of 27 counts that problem. A tie broken the other way would score 26.

Twenty-three problems are unanimous, eight samples and one answer, and all 23 answers are gold. Their mean length is 18480 tokens. Five problems are wrong on the first sample: 10, 13, 14, 15, and 30. Two more, 7 and 20, are correct on the first sample and not unanimous.

| Problem | Gold | First sample | Vote | Correct in 8 | The pool of eight |
| --- | --- | --- | --- | --- | --- |
| 7 | 821 | 821 | 821 | 7 | one sample disagrees |
| 20 | 336 | 336 | 336 | 5 | the other three answers differ |
| 10 | 81 | 70 | 81 | 3 | three later samples recover 81 |
| 30 | 240 | 752 | 240 | 3 | ties 752 at three votes each |
| 13 | 204 | none | 79 | 0 | the mode is 79, with 4 of 8 |
| 14 | 60 | 63 | 63 | 0 | no answer has more than 2 votes |
| 15 | 735 | 147 | 147 | 0 | 147 has 6 of 8 |

Problem 15 already looks like a confident wrong mode in the eight: 6 samples agree on 147. Problem 13's mode is 79, with 4 of 8, and three traces box no integer. Problem 14 has no answer with more than 2 votes, which is what a small pool looks like when a weak mode has not separated yet.

Twenty-four further draws on each of these three problems, seeds continued from the same rule, all 72 stopped, and none boxed the gold answer. Across the 32 traces, problem 13 lands on 79 sixteen times and boxes no integer thirteen times. Problem 14's scatter resolves: 63 has 14 of 32. Problem 15 lands on 147 twenty-three times. A per-sample hit rate of 0.09 would still have left about a 1 in 20 chance of missing all 32 draws, so these counts do not prove the gold answer has probability zero. They do show that the errors are stable modes. A wider vote keeps returning 79, 63, and 147. The two problems the vote of eight repaired, 10 and 30, were problems where the gold answer was already in the pool.

Wrong traces are longer. Across the 240 traces, the 202 correct ones average 19712 tokens and the 38 incorrect ones average 38375, a ratio of 1.95. Separately, tokens per problem from one sample to eight scale by 8.15, against a width ratio of 8.

## What would reverse the ranking

The log split on AIME is \(+0.077\) from accuracy and \(-2.098\) from length. A reversal inside this definition has to come from \(\beta\) or \(\rho\), the two factors we did not measure, and it has to be large. From one sample to eight, their product would need to multiply by more than \(8.15/1.08\), a factor of about 7.5, to offset the tokens. Nothing in the vote margins, the box position, or the verifier ratings on the medium band is a measurement of that factor. The verifier ratings there are 0.864 on correct solutions and 0.812 on incorrect ones, which is why selection lost to the vote. The box sits at the end of the trace, which says an early cut drops the answer, and does not say what fraction of the preceding tokens the answer depends on.

The one place \(A/\tau\) rose was the short budget on the easy band, from 0.770 at a cap of 512 to 1.671 at a cap of 1024. Accuracy multiplied by 2.40 and tokens by 1.11, because finished traces stopped spending the allowance. That is the assumption the width proposition names when it fails: cost did not grow with the allowance. Once the traces can finish, the remaining axis is the number of samples, the cost is linear again, and \(A/\tau\) falls.

## Conclusion

Parallel independent samples lower \(A/\tau\) on every finished pool in this note, and the width that maximizes \(A/\tau\) is one sample. Accuracy stays at 1 on the easy band, rises along the medium prefix up to the accuracy fixed by how that band was built, and on AIME moves from 25 of 30 to 27 of 30. That AIME sample scores 83.3 and sits beside the published 81.3 for this 4B checkpoint, on one seed. Eight samples score 90.0 and multiply the read by 8.15. The accuracy ratio, 1.08, and the best ratio a perfect pool could have reached from this one-sample baseline, 1.20, are both below the token bar. The three problems still wrong at eight samples are still wrong at 32 samples, on stable wrong answers. Reflection at a matched budget ties an independent resample. The serial alternative we measured does not overturn the ranking.

\(\beta\) and \(\rho\) are still unmeasured, so the reported score is \(A/\tau\) with \(\alpha=1\), not full STU. A reversal would be a real finding about attention or about relevance. It would not require a new definition. The numbers above are recomputed from the saved traces by `experiments/analyze.py`.

## References

```refs
wei2022 | Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q., and Zhou, D. Chain-of-thought prompting elicits reasoning in large language models. In NeurIPS, 2022. https://arxiv.org/abs/2201.11903
openai2024 | OpenAI. Learning to reason with LLMs. 2024. https://openai.com/index/learning-to-reason-with-llms/
deepseekr1 | DeepSeek-AI. DeepSeek-R1: Incentivizing reasoning capability in LLMs via reinforcement learning. arXiv:2501.12948, 2025. https://arxiv.org/abs/2501.12948
muennighoff2025 | Muennighoff, N., Yang, Z., Shi, W., Li, X. L., Fei-Fei, L., Hajishirzi, H., Zettlemoyer, L., Liang, P., Candès, E., and Hashimoto, T. s1: Simple test-time scaling. arXiv:2501.19393, 2025. https://arxiv.org/abs/2501.19393
snell2024 | Snell, C., Lee, J., Xu, K., and Kumar, A. Scaling LLM test-time compute optimally can be more effective than scaling model parameters. arXiv:2408.03314, 2024. https://arxiv.org/abs/2408.03314
wang2023 | Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., and Zhou, D. Self-consistency improves chain of thought reasoning in language models. In ICLR, 2023. https://arxiv.org/abs/2203.11171
aime | Mathematical Association of America. American Invitational Mathematics Examination. https://maa.org/math-competitions/
qwen3think | Qwen Team. Qwen3-4B-Thinking-2507. 2025. https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507
qwen3 | Qwen Team. Qwen3 technical report. arXiv:2505.09388, 2025. https://arxiv.org/abs/2505.09388
brown2024 | Brown, B., Juravsky, J., Ehrlich, R., Clark, R., Le, Q. V., Ré, C., and Mirhoseini, A. Large language monkeys: Scaling inference compute with repeated sampling. arXiv:2407.21787, 2024. https://arxiv.org/abs/2407.21787
chen2021 | Chen, M., Tworek, J., Jun, H., Yuan, Q., Pinto, H. P. de O., Kaplan, J., Edwards, H., Burda, Y., Joseph, N., Brockman, G., et al. Evaluating large language models trained on code. arXiv:2107.03374, 2021. https://arxiv.org/abs/2107.03374
cobbe2021 | Cobbe, K., Kosaraju, V., Bavarian, M., Chen, M., Jun, H., Kaiser, L., Plappert, M., Tworek, J., Hilton, J., Nakano, R., Hesse, C., and Schulman, J. Training verifiers to solve math word problems. arXiv:2110.14168, 2021. https://arxiv.org/abs/2110.14168
uesato2022 | Uesato, J., Kushman, N., Kumar, R., Song, F., Siegel, N., Wang, L., Creswell, A., Irving, G., and Higgins, I. Solving math word problems with process- and outcome-based feedback. arXiv:2211.14275, 2022. https://arxiv.org/abs/2211.14275
lightman2024 | Lightman, H., Kosaraju, V., Burda, Y., Edwards, H., Baker, B., Lee, T., Leike, J., Schulman, J., Sutskever, I., and Cobbe, K. Let's verify step by step. In ICLR, 2024. https://arxiv.org/abs/2305.20050
deepseekmath | Shao, Z., Wang, P., Zhu, Q., Xu, R., Song, J., Bi, X., Zhang, H., Zhang, M., Li, Y. K., Wu, Y., and Guo, D. DeepSeekMath: Pushing the limits of mathematical reasoning in open language models. arXiv:2402.03300, 2024. https://arxiv.org/abs/2402.03300
huang2024 | Huang, J., Chen, X., Mishra, S., Zheng, H. S., Yu, A. W., Song, X., and Zhou, D. Large language models cannot self-correct reasoning yet. In ICLR, 2024. https://arxiv.org/abs/2310.01798
madaan2023 | Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., Alon, U., Dziri, N., Prabhumoye, S., Yang, Y., et al. Self-Refine: Iterative refinement with self-feedback. In NeurIPS, 2023. https://arxiv.org/abs/2303.17651
shinn2023 | Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., and Yao, S. Reflexion: Language agents with verbal reinforcement learning. In NeurIPS, 2023. https://arxiv.org/abs/2303.11366
hendrycks2021 | Hendrycks, D., Burns, C., Kadavath, S., Arora, A., Basart, S., Tang, E., Song, D., and Steinhardt, J. Measuring mathematical problem solving with the MATH dataset. In NeurIPS, 2021. https://arxiv.org/abs/2103.03874
deepseekv3 | DeepSeek-AI. DeepSeek-V3 technical report. arXiv:2412.19437, 2024. https://arxiv.org/abs/2412.19437
vaswani2017 | Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., and Polosukhin, I. Attention is all you need. In NeurIPS, 2017. https://arxiv.org/abs/1706.03762
kojima2022 | Kojima, T., Gu, S. S., Reid, M., Matsuo, Y., and Iwasawa, Y. Large language models are zero-shot reasoners. In NeurIPS, 2022. https://arxiv.org/abs/2205.11916
yao2023 | Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., and Narasimhan, K. Tree of Thoughts: Deliberate problem solving with large language models. In NeurIPS, 2023. https://arxiv.org/abs/2305.10601
mathshepherd | Wang, P., Li, L., Shao, Z., Xu, R. X., Dai, D., Li, Y., Chen, D., Wu, Y., and Sui, Z. Math-Shepherd: Verify and reinforce LLMs step-by-step without human annotations. arXiv:2312.08935, 2023. https://arxiv.org/abs/2312.08935
welleck2023 | Welleck, S., Lu, X., West, P., Brahman, F., Shen, T., Khashabi, D., and Choi, Y. Generating sequences by learning to self-correct. In ICLR, 2023. https://arxiv.org/abs/2211.00053
lewkowycz2022 | Lewkowycz, A., Andreassen, A., Dohan, D., Dyer, E., Michalewski, H., Ramasesh, V., Slone, A., Anil, C., Schlag, I., Gutman-Solo, T., et al. Solving quantitative reasoning problems with language models. In NeurIPS, 2022. https://arxiv.org/abs/2206.14858
```

