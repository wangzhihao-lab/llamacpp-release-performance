# E43: b6556 → b6708 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 (not listed) | b6556→b6708 | -1.5% | -0.8% (19.3%, ++-) | +15.6% (10.0%) | -4.0%/+12.7% | info |
| tinyllama-1.1b/cpu/tg128 | b6556→b6708 | -13.8% | +0.5% (34.9%, ++-) | +1.6% (14.0%) | -8.2%/+8.2% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
