# E48: b7464 → b7595 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b7464→b7595 | -22.1% | -0.0% (10.0%, -++) | +0.1% (10.0%) | +0.1%/+28.7% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b7464→b7595 | -2.9% | +0.0% (10.0%, -++) | +0.3% (10.0%) | +35.8%/+40.3% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
