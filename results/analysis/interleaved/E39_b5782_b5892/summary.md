# E39: b5782 → b5892 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b5782→b5892 | -27.3% | +0.4% (11.4%, +-+) | +0.3% (10.0%) | -0.8%/+36.8% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b5782→b5892 | +5.8% | -0.4% (10.0%, +--) | +1.7% (10.0%) | +34.3%/+29.2% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
