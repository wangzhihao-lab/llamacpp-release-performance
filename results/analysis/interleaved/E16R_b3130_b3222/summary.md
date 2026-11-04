# E16R: b3130 → b3222 (step-1 class C)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b3130→b3222 | +33.5% | +22.8% (22.0%, +++) | +28.3% (10.0%) | +38.6%/+33.2% | C |
| mistral-7b/cpu/tg128 (not listed) | b3130→b3222 | +11.4% | +6.6% (35.1%, +++) | +3.8% (10.0%) | +69.1%/+57.6% | info |
| mistral-7b/metal/pp512 | b3130→b3222 | +14.4% | +0.5% (10.0%, ++-) | +0.1% (10.0%) | +47.7%/+29.3% | noise |
| mistral-7b/metal/tg128 (not listed) | b3130→b3222 | +2.0% | +0.4% (10.0%, ++-) | -0.6% (10.0%) | +48.5%/+44.7% | info |
| qwen2.5-1.5b/cpu/pp512 | b3130→b3222 | +29.5% | +23.7% (10.0%, +++) | +25.9% (10.3%) | +58.1%/+53.8% | C |
| qwen2.5-1.5b/cpu/tg128 | b3130→b3222 | +14.8% | +2.1% (12.2%, +++) | +8.0% (10.0%) | +86.7%/+75.8% | noise |
| tinyllama-1.1b/cpu/pp512 | b3130→b3222 | +40.0% | +9.8% (10.0%, +++) | +9.8% (10.0%) | +67.8%/+31.6% | noise |
| tinyllama-1.1b/cpu/tg128 (not listed) | b3130→b3222 | +10.8% | +5.6% (14.6%, +++) | +9.4% (10.0%) | +97.5%/+95.0% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
