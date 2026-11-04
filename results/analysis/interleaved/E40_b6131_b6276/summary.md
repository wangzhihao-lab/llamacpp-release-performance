# E40: b6131 → b6276 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b6131→b6276 | +39.7% | -4.9% (74.9%, --+) | +0.6% (48.3%) | +12.4%/-19.1% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b6131→b6276 | +13.5% | +9.0% (139.6%, +-+) | -0.4% (81.7%) | +7.3%/-5.9% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
