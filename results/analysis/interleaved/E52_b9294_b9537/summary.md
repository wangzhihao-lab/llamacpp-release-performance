# E52: b9294 → b9537 (step-1 class D)

Event verdict: **A**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 | b9294→b9537 | +12.5% | -3.1% (22.1%, -+-) | +31.3% (18.7%) | -16.1%/-2.1% | A |
| tinyllama-1.1b/cpu/tg128 (not listed) | b9294→b9537 | +11.1% | -6.2% (67.7%, -++) | +24.0% (19.7%) | -12.6%/-2.5% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
