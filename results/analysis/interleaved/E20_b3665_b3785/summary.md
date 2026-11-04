# E20: b3665 → b3785 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/metal/pp512 | b3665→b3785 | +114.4% | +15.7% (56.4%, -++) | +1.2% (37.8%) | +89.8%/-10.5% | noise |
| qwen2.5-1.5b/metal/tg128 (not listed) | b3665→b3785 | -7.3% | +12.0% (36.6%, +++) | -6.1% (35.5%) | +61.6%/+63.7% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
