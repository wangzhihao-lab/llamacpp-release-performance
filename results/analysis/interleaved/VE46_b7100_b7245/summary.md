# VE46: b7100 → b7245 (step-1 class V)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/cpu/pp512 | b7100→b7245 | -4.2% | -8.1% (28.1%, ---) | +4.0% (10.0%) | +13.2%/+22.9% | noise |
| qwen2.5-1.5b/cpu/tg128 | b7100→b7245 | -2.7% | -8.3% (48.1%, -+-) | +7.8% (11.9%) | +10.0%/+21.8% | noise |
| qwen2.5-1.5b/metal/pp512 | b7100→b7245 | -6.3% | -0.4% (14.8%, +--) | +0.1% (10.0%) | +40.0%/+49.5% | noise |
| qwen2.5-1.5b/metal/tg128 | b7100→b7245 | -7.2% | +3.3% (21.5%, ++-) | +2.7% (10.0%) | +51.9%/+68.1% | noise |
| tinyllama-1.1b/metal/pp512 | b7100→b7245 | +22.7% | -0.0% (10.0%, -+-) | +0.2% (10.0%) | +29.1%/+5.4% | noise |
| tinyllama-1.1b/metal/tg128 | b7100→b7245 | +20.1% | +0.1% (10.0%, -++) | +0.2% (10.0%) | +38.7%/+15.7% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
