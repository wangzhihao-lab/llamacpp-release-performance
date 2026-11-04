# E07: b1778 → b1939 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 (not listed) | b1778→b1939 | +8.6% | -0.8% (44.1%, +-+) | +7.3% (10.0%) | +32.1%/+30.6% | info |
| tinyllama-1.1b/cpu/tg128 | b1778→b1939 | +30.7% | -4.5% (65.4%, --+) | +5.1% (10.0%) | +127.7%/+83.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
