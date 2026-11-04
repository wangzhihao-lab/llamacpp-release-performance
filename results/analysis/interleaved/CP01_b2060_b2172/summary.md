# CP01: b2060 → b2172 (step-1 class CP)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b2060→b2172 | -42.2% | -0.3% (10.0%, ---) | -0.2% (10.0%) | +15.5%/+99.3% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b2060→b2172 | +3.3% | -0.3% (10.0%, --+) | +0.2% (10.0%) | +68.9%/+63.9% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
