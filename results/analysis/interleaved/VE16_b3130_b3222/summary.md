# VE16: b3130 → b3222 (step-1 class V)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/metal/pp512 | b3130→b3222 | -12.6% | +1.9% (36.7%, -++) | +8.2% (30.6%) | +72.0%/+113.0% | noise |
| qwen2.5-1.5b/metal/tg128 | b3130→b3222 | -5.5% | +1.5% (28.9%, --+) | +5.0% (12.1%) | +58.6%/+76.1% | noise |
| tinyllama-1.1b/metal/pp512 | b3130→b3222 | -6.0% | -0.0% (10.0%, -+-) | +0.0% (10.0%) | +87.7%/+99.7% | noise |
| tinyllama-1.1b/metal/tg128 | b3130→b3222 | -5.3% | -0.2% (10.0%, +--) | -0.1% (10.0%) | +49.0%/+57.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
