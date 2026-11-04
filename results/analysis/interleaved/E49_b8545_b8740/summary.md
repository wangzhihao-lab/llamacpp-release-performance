# E49: b8545 → b8740 (step-1 class C)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b8545→b8740 | +77.8% | +58.9% (40.3%, +++) | +66.3% (17.4%) | -28.5%/-33.2% | C |
| mistral-7b/metal/tg128 (not listed) | b8545→b8740 | -1.5% | -4.9% (19.4%, ---) | -1.1% (10.0%) | -16.0%/-15.6% | info |
| qwen2.5-1.5b/metal/pp512 | b8545→b8740 | +79.9% | +83.5% (49.0%, +++) | +106.9% (54.1%) | +2.9%/+18.3% | C |
| qwen2.5-1.5b/metal/tg128 (not listed) | b8545→b8740 | -1.5% | +1.2% (26.6%, +-+) | +3.9% (16.5%) | +27.1%/+34.0% | info |
| tinyllama-1.1b/metal/pp512 | b8545→b8740 | +85.5% | +95.9% (34.8%, +++) | +114.3% (38.4%) | +10.9%/+28.1% | C |
| tinyllama-1.1b/metal/tg128 (not listed) | b8545→b8740 | -3.1% | +0.9% (18.2%, +--) | +0.4% (15.4%) | +29.3%/+34.1% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
