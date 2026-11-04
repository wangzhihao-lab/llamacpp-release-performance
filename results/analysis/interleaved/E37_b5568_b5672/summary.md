# E37: b5568 → b5672 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 (not listed) | b5568→b5672 | +5.2% | -6.5% (114.7%, -+-) | +14.5% (22.8%) | -23.0%/-16.2% | info |
| tinyllama-1.1b/cpu/tg128 | b5568→b5672 | +24.0% | -11.1% (179.0%, -+-) | +21.0% (34.1%) | -19.2%/-21.2% | noise |
| tinyllama-1.1b/metal/pp512 | b5568→b5672 | -28.9% | -4.3% (70.7%, ++-) | -12.5% (37.5%) | -2.8%/+19.5% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b5568→b5672 | -9.9% | -7.4% (74.7%, +--) | -30.5% (253.3%) | -24.7%/-41.9% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
