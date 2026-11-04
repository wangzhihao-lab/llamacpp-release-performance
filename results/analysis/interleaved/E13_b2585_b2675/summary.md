# E13: b2585 → b2675 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b2585→b2675 | -15.8% | +0.1% (10.0%, -++) | +0.6% (10.0%) | +28.7%/+53.8% | noise |
| mistral-7b/metal/tg128 (not listed) | b2585→b2675 | -7.6% | -0.7% (10.1%, -++) | -1.2% (10.0%) | +35.8%/+45.2% | info |
| tinyllama-1.1b/cpu/pp512 | b2585→b2675 | -13.9% | +1.1% (17.9%, +-+) | +2.8% (10.0%) | +43.8%/+71.8% | noise |
| tinyllama-1.1b/cpu/tg128 | b2585→b2675 | -12.5% | +1.2% (16.2%, +-+) | -0.5% (10.0%) | +72.9%/+96.6% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
