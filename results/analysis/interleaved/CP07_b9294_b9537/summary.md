# CP07: b9294 → b9537 (step-1 class CP)

Event verdict: **A**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/cpu/pp512 | b9294→b9537 | +8.0% | +1.5% (10.0%, ++-) | +13.6% (10.0%) | +13.3%/+19.1% | A |
| qwen2.5-1.5b/cpu/tg128 (not listed) | b9294→b9537 | +5.6% | +1.3% (11.7%, ++-) | +12.2% (10.6%) | +14.2%/+21.3% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
