# E29: b4545 → b4671 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 | b4545→b4671 | +14.5% | -3.2% (12.0%, --+) | +2.3% (10.0%) | +32.8%/+18.7% | noise |
| tinyllama-1.1b/cpu/tg128 | b4545→b4671 | +21.6% | -0.2% (19.5%, -+-) | +7.1% (14.3%) | +67.1%/+47.1% | noise |
| tinyllama-1.1b/metal/pp512 | b4545→b4671 | -25.8% | -0.0% (10.0%, -+-) | +0.0% (10.0%) | +3.5%/+39.6% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b4545→b4671 | +15.1% | -0.0% (10.0%, --+) | -0.1% (10.0%) | +51.7%/+31.7% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
