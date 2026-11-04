# E36: b5416 → b5568 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 (not listed) | b5416→b5568 | -1.6% | +9.2% (41.2%, -++) | +5.9% (14.4%) | -4.2%/+3.1% | info |
| tinyllama-1.1b/cpu/tg128 | b5416→b5568 | -15.7% | +2.3% (62.6%, -++) | +14.8% (40.0%) | -19.2%/+10.1% | noise |
| tinyllama-1.1b/metal/pp512 | b5416→b5568 | +42.2% | +2.1% (37.3%, ++-) | +3.1% (52.2%) | +18.4%/-14.2% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b5416→b5568 | +11.3% | +3.1% (19.3%, +++) | +8.3% (13.8%) | +18.4%/+15.2% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
