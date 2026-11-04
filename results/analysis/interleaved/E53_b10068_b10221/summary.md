# E53: b10068 → b10221 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 (not listed) | b10068→b10221 | +21.9% | +0.5% (52.2%, +-+) | +2.4% (12.1%) | +19.5%/+0.4% | info |
| tinyllama-1.1b/metal/tg128 | b10068→b10221 | +54.3% | +0.3% (17.2%, +-+) | +3.4% (16.3%) | +33.1%/-10.8% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
