# E44: b6815 → b6948 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 (not listed) | b6815→b6948 | -7.6% | +0.8% (21.6%, +--) | -6.2% (12.4%) | +27.2%/+29.2% | info |
| tinyllama-1.1b/cpu/tg128 | b6815→b6948 | -23.9% | -2.3% (28.1%, +-+) | +12.2% (14.5%) | +30.0%/+91.7% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
