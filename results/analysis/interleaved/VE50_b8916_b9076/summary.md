# VE50: b8916 → b9076 (step-1 class V)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b8916→b9076 | -1.2% | +2.7% (15.0%, +-+) | -0.9% (10.0%) | -2.1%/-1.8% | noise |
| mistral-7b/cpu/tg128 | b8916→b9076 | +7.7% | +2.8% (16.7%, ++-) | -0.6% (11.8%) | +13.0%/+4.3% | noise |
| qwen2.5-1.5b/cpu/pp512 | b8916→b9076 | +2.0% | +2.0% (13.3%, +++) | +4.3% (10.0%) | +5.0%/+7.4% | noise |
| qwen2.5-1.5b/cpu/tg128 | b8916→b9076 | +2.7% | +1.5% (11.3%, +++) | +8.2% (10.0%) | +2.4%/+7.9% | noise |
| qwen2.5-1.5b/metal/pp512 | b8916→b9076 | +45.0% | +34.8% (29.5%, +++) | +31.8% (10.0%) | +66.4%/+51.3% | C |
| qwen2.5-1.5b/metal/tg128 | b8916→b9076 | +2.9% | -0.6% (14.8%, --+) | +6.3% (10.0%) | +70.8%/+76.4% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
