# CP02: b3785 → b3935 (step-1 class CP)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 (not listed) | b3785→b3935 | +0.4% | -0.4% (14.9%, -++) | +0.1% (10.0%) | +24.1%/+23.7% | info |
| mistral-7b/cpu/tg128 | b3785→b3935 | +9.3% | +1.4% (12.9%, -++) | +1.2% (10.0%) | +50.5%/+39.4% | noise |
| qwen2.5-1.5b/metal/pp512 (not listed) | b3868→b3935 | +22.5% | +1.1% (21.0%, +--) | +0.1% (10.0%) | +90.6%/+55.7% | info |
| qwen2.5-1.5b/metal/tg128 | b3868→b3935 | +8.7% | +1.8% (15.1%, +-+) | +0.1% (10.0%) | +73.5%/+59.8% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
