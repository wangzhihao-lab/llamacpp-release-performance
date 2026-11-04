# E30: b4671 → b4754 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b4671→b4754 | +37.5% | +0.1% (10.0%, ++-) | +0.2% (10.0%) | +37.6%/+0.2% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b4671→b4754 | -7.0% | +0.0% (10.0%, ++-) | -0.2% (10.0%) | +31.3%/+40.9% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
