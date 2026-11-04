# VE03: b1505 → b1561 (step-1 class V)

Event verdict: **incomplete**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b1505→b1561 | +0.4% | -3.9% (28.7%, -+-) | -0.2% (10.0%) | +18.0%/+17.4% | noise |
| mistral-7b/metal/tg128 | b1505→b1561 | +0.7% | -0.4% (16.2%, -+-) | -1.1% (10.0%) | +33.3%/+30.9% | noise |
| qwen2.5-1.5b/cpu/pp512 | b1505→b1561 | +0.0% | n/a | n/a | n/a | incomplete |
| qwen2.5-1.5b/cpu/tg128 | b1505→b1561 | +0.0% | n/a | n/a | n/a | incomplete |
| qwen2.5-1.5b/metal/pp512 | b1505→b1561 | +0.0% | n/a | n/a | n/a | incomplete |
| qwen2.5-1.5b/metal/tg128 | b1505→b1561 | +0.0% | n/a | n/a | n/a | incomplete |
| tinyllama-1.1b/metal/pp512 | b1505→b1561 | -3.8% | -0.2% (10.0%, -+-) | +0.1% (10.0%) | +1.5%/+5.7% | noise |
| tinyllama-1.1b/metal/tg128 | b1505→b1561 | -20.3% | -0.3% (10.0%, -+-) | -0.4% (10.0%) | +23.8%/+54.7% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
