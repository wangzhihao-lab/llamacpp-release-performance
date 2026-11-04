# CP05: b4942 → b5056 (step-1 class CP)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 (not listed) | b4942→b5056 | -1.3% | -8.1% (19.0%, ---) | -0.4% (10.0%) | +4.9%/+5.9% | info |
| mistral-7b/cpu/tg128 | b4942→b5056 | +8.8% | -9.0% (24.1%, ---) | +0.6% (10.9%) | +32.0%/+22.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
