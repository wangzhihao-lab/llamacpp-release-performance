# E18: b3355 → b3449 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b3355→b3449 | +11.2% | +0.2% (10.0%, ++-) | +10.1% (18.9%) | +31.7%/+30.4% | noise |
| mistral-7b/metal/tg128 (not listed) | b3355→b3449 | +6.2% | -0.0% (16.2%, +-+) | +6.6% (10.0%) | +29.5%/+30.0% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
