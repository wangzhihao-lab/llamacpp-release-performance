# E10: b2172 → b2330 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b2172→b2330 | -11.8% | -3.0% (17.6%, -+-) | +0.5% (10.0%) | +20.8%/+37.7% | noise |
| mistral-7b/cpu/tg128 (not listed) | b2172→b2330 | -24.0% | +5.3% (19.8%, +++) | -2.5% (10.0%) | +24.9%/+60.1% | info |
| tinyllama-1.1b/cpu/pp512 (not listed) | b2172→b2330 | +29.1% | +0.8% (35.2%, +-+) | +4.8% (16.1%) | +74.7%/+41.8% | info |
| tinyllama-1.1b/cpu/tg128 | b2172→b2330 | +36.0% | +6.0% (30.7%, +-+) | +4.7% (10.0%) | +109.2%/+61.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
