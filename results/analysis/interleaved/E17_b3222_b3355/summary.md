# E17: b3222 → b3355 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b3222→b3355 | -20.2% | -3.2% (36.2%, -+-) | +2.2% (10.0%) | +9.1%/+39.6% | noise |
| mistral-7b/metal/tg128 (not listed) | b3222→b3355 | -8.0% | +5.5% (64.9%, -++) | +0.5% (11.2%) | +13.7%/+24.2% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
