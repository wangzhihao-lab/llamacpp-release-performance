# E42: b6424 → b6556 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b6424→b6556 | +41.0% | +0.2% (28.0%, +--) | +2.9% (58.1%) | +21.3%/-11.4% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b6424→b6556 | +7.6% | -7.1% (11.2%, ---) | -0.5% (14.0%) | +19.5%/+10.5% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
