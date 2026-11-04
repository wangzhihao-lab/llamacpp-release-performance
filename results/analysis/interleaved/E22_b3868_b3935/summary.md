# E22: b3868 → b3935 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/cpu/pp512 | b3868→b3935 | +16.6% | +2.0% (15.0%, +-+) | +13.0% (16.1%) | +19.2%/+15.5% | noise |
| qwen2.5-1.5b/cpu/tg128 (not listed) | b3868→b3935 | +6.0% | +8.4% (43.7%, +++) | +5.8% (10.0%) | +18.3%/+18.1% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
