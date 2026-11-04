# CP06: b7100 → b7245 (step-1 class CP)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/metal/pp512 (not listed) | b7100→b7245 | -6.3% | -0.2% (10.0%, ---) | +0.1% (10.0%) | +41.9%/+51.5% | info |
| qwen2.5-1.5b/metal/tg128 | b7100→b7245 | -7.2% | -0.1% (10.0%, +-+) | +2.4% (10.0%) | +56.7%/+73.0% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
