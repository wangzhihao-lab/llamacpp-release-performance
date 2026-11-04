# E47: b7245 → b7464 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b7245→b7464 | -14.8% | -1.1% (35.0%, -++) | +0.3% (10.0%) | -10.7%/+5.1% | noise |
| mistral-7b/metal/tg128 | b7245→b7464 | -19.2% | -1.8% (41.5%, -+-) | -3.9% (10.0%) | -9.0%/+8.3% | noise |
| tinyllama-1.1b/cpu/pp512 | b7245→b7464 | -18.6% | +1.8% (11.9%, +-+) | +5.4% (10.0%) | -3.8%/+24.6% | noise |
| tinyllama-1.1b/cpu/tg128 | b7245→b7464 | -28.0% | +2.3% (25.4%, +-+) | +9.7% (16.1%) | -2.4%/+48.6% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
