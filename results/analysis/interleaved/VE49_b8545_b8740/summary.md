# VE49: b8545 → b8740 (step-1 class V)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b8545→b8740 | +0.5% | +2.4% (10.0%, -++) | -1.2% (10.0%) | -0.1%/-1.8% | noise |
| mistral-7b/cpu/tg128 | b8545→b8740 | -0.1% | +2.0% (16.6%, -++) | -0.7% (10.8%) | +5.1%/+4.5% | noise |
| qwen2.5-1.5b/cpu/pp512 | b8545→b8740 | -0.7% | +1.2% (10.0%, ++-) | +4.8% (10.0%) | +7.3%/+13.2% | noise |
| qwen2.5-1.5b/cpu/tg128 | b8545→b8740 | -0.9% | +0.6% (10.0%, ++-) | +7.7% (11.9%) | +2.5%/+11.4% | noise |
| tinyllama-1.1b/cpu/pp512 | b8545→b8740 | -0.1% | -0.5% (10.0%, -+-) | +5.1% (12.8%) | +9.5%/+15.2% | noise |
| tinyllama-1.1b/cpu/tg128 | b8545→b8740 | -0.8% | +0.2% (19.6%, -+-) | +10.7% (13.4%) | +29.2%/+44.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
