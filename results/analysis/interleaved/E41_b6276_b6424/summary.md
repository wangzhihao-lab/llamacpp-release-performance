# E41: b6276 → b6424 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b6276→b6424 | -28.6% | +13.8% (273.3%, -++) | -54.4% (138.2%) | -5.2%/-39.4% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b6276→b6424 | -12.2% | +0.3% (122.9%, -++) | -7.1% (128.6%) | -39.0%/-35.5% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
