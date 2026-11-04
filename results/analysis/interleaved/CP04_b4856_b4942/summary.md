# CP04: b4856 → b4942 (step-1 class CP)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/metal/pp512 (not listed) | b4856→b4942 | +9.2% | +0.0% (10.0%, --+) | +0.1% (10.0%) | +56.0%/+42.9% | info |
| qwen2.5-1.5b/metal/tg128 | b4856→b4942 | +17.8% | -0.4% (10.0%, ---) | -0.1% (10.0%) | +70.0%/+44.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
