# E21: b3785 → b3868 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/metal/pp512 | b3785→b3868 | -44.8% | -6.9% (36.4%, -+-) | +37.9% (75.3%) | -43.7%/+40.7% | noise |
| qwen2.5-1.5b/metal/tg128 (not listed) | b3785→b3868 | +10.0% | -5.7% (21.1%, ---) | +10.5% (41.9%) | +38.5%/+39.2% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
