# Verifier Bottleneck for Math LLMs

Structural task utilization for test-time scaling. GitHub renders display math only between `$$`, not between `\[` and `\]`.

$$
\mathrm{STU}=\frac{A\cdot\beta\cdot\rho}{\alpha\cdot\tau}
$$

The note itself is on the `blog` branch. Edit `src/stu.md`, then:

```bash
python3 build_site.py
```

Open `index.html`. Research notes under `docs/` and `metrics/` stay on the local machine and are not tracked.
