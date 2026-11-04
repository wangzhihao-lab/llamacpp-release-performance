# E35: b5159 → b5273 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b5159→b5273 | -29.0% | +0.9% (21.0%, +-+) | -0.5% (10.0%) | -0.7%/+39.3% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b5159→b5273 | +1.1% | -0.4% (10.0%, +-+) | -0.4% (10.0%) | +26.7%/+24.9% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
