# E33: b4942 → b5056 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 (not listed) | b4942→b5056 | -8.2% | -5.1% (28.5%, -++) | -0.1% (10.0%) | -7.3%/+0.8% | info |
| mistral-7b/metal/tg128 | b4942→b5056 | -12.3% | -2.5% (22.9%, -++) | -0.5% (10.0%) | -3.8%/+9.1% | noise |
| qwen2.5-1.5b/cpu/pp512 | b4942→b5056 | -14.8% | +1.4% (10.0%, +++) | +13.6% (10.0%) | -1.3%/+31.6% | noise |
| qwen2.5-1.5b/cpu/tg128 (not listed) | b4942→b5056 | -7.2% | +0.1% (10.0%, ++-) | +9.8% (10.2%) | +3.3%/+22.2% | info |
| tinyllama-1.1b/cpu/pp512 (not listed) | b4942→b5056 | -4.2% | +0.5% (11.4%, ++-) | +4.3% (10.0%) | -1.2%/+7.5% | info |
| tinyllama-1.1b/cpu/tg128 | b4942→b5056 | -29.2% | -2.1% (19.9%, -+-) | +9.9% (22.2%) | +4.9%/+62.7% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
