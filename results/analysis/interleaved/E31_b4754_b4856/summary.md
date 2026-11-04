# E31: b4754 → b4856 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 | b4754→b4856 | -9.7% | +1.9% (12.5%, ++-) | +3.2% (10.0%) | +19.8%/+36.8% | noise |
| tinyllama-1.1b/cpu/tg128 | b4754→b4856 | -16.4% | +0.4% (25.6%, ++-) | +6.6% (21.5%) | +43.8%/+83.5% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
