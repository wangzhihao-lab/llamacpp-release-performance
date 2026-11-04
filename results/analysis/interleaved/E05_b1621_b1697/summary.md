# E05: b1621 → b1697 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 (not listed) | b1621→b1697 | +9.3% | -0.2% (15.6%, +-+) | +1.6% (10.0%) | +19.8%/+11.4% | info |
| tinyllama-1.1b/cpu/tg128 | b1621→b1697 | +21.9% | +1.2% (32.7%, +-+) | +3.5% (10.0%) | +59.9%/+35.9% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
