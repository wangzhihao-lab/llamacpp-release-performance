# E02: b1245 → b1505 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 (not listed) | b1245→b1505 | -5.7% | -2.4% (25.0%, --+) | +6.1% (15.2%) | -20.1%/-10.2% | info |
| mistral-7b/metal/tg128 | b1245→b1505 | -10.8% | -6.5% (24.2%, ---) | +13.0% (10.0%) | -18.6%/+3.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
