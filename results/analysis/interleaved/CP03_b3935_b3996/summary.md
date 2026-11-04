# CP03: b3935 → b3996 (step-1 class CP)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b3935→b3996 | +50.9% | +0.2% (10.0%, +++) | +0.2% (10.0%) | +53.8%/+2.2% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b3935→b3996 | +17.9% | -0.4% (10.0%, ---) | -0.3% (10.0%) | +64.9%/+39.4% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
