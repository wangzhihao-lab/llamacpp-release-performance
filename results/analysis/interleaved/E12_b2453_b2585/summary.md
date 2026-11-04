# E12: b2453 → b2585 (step-1 class C)

Event verdict: **A**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b2453→b2585 | +14.1% | +1.3% (17.2%, -++) | +5.0% (10.0%) | +38.2%/+27.1% | noise |
| mistral-7b/metal/tg128 (not listed) | b2453→b2585 | +4.8% | -2.0% (18.1%, -++) | +1.0% (10.0%) | +38.7%/+33.6% | info |
| tinyllama-1.1b/cpu/pp512 | b2453→b2585 | +17.3% | +8.4% (17.6%, +++) | +11.1% (10.0%) | +57.2%/+48.9% | A |
| tinyllama-1.1b/cpu/tg128 (not listed) | b2453→b2585 | +5.2% | +1.6% (17.6%, +-+) | +2.7% (10.0%) | +82.3%/+78.0% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
