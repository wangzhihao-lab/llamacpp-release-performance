# E54: b10221 → b10451 (step-1 class A)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b10221→b10451 | -11.5% | -1.1% (22.9%, -+-) | +0.4% (11.5%) | +5.5%/+19.8% | noise |
| mistral-7b/metal/tg128 | b10221→b10451 | -10.6% | +0.8% (14.1%, -++) | +0.6% (10.0%) | +14.9%/+29.3% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
