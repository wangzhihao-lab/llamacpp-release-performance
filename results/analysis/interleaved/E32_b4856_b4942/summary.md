# E32: b4856 → b4942 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b4856→b4942 | +21.1% | -7.4% (73.6%, -++) | +1.2% (14.0%) | -21.9%/-34.8% | noise |
| mistral-7b/metal/tg128 | b4856→b4942 | +25.7% | -13.4% (66.1%, --+) | -0.3% (10.0%) | -17.7%/-34.7% | noise |
| qwen2.5-1.5b/cpu/pp512 | b4856→b4942 | +17.1% | -0.4% (16.9%, --+) | +7.5% (10.0%) | +2.8%/-5.6% | noise |
| qwen2.5-1.5b/cpu/tg128 (not listed) | b4856→b4942 | +17.3% | +0.5% (10.0%, ++-) | +2.1% (10.0%) | +10.2%/-4.1% | info |
| tinyllama-1.1b/cpu/pp512 | b4856→b4942 | +26.2% | -0.2% (10.0%, -+-) | +5.4% (10.0%) | +7.2%/-10.5% | noise |
| tinyllama-1.1b/cpu/tg128 | b4856→b4942 | +47.5% | -3.7% (16.5%, ---) | +8.0% (14.3%) | +10.6%/-19.0% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
