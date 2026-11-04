# AA1: b11559 → b11559 (step-1 class AA)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b11559→b11559 | +0.0% | +0.7% (10.0%, +--) | +0.8% (10.0%) | +4.8%/+5.6% | noise |
| mistral-7b/cpu/tg128 | b11559→b11559 | +0.0% | +0.7% (10.0%, ++-) | +0.5% (10.4%) | +13.8%/+14.3% | noise |
| mistral-7b/metal/pp512 | b11559→b11559 | +0.0% | +0.5% (11.1%, +--) | +0.5% (10.0%) | +25.0%/+25.6% | noise |
| mistral-7b/metal/tg128 | b11559→b11559 | +0.0% | +1.5% (10.0%, +--) | -0.4% (10.0%) | +32.7%/+32.2% | noise |
| qwen2.5-1.5b/cpu/pp512 | b11559→b11559 | +0.0% | -0.0% (10.0%, --+) | +5.0% (10.0%) | +15.2%/+20.9% | noise |
| qwen2.5-1.5b/cpu/tg128 | b11559→b11559 | +0.0% | +0.2% (11.3%, -++) | +5.4% (11.8%) | +17.8%/+24.2% | noise |
| qwen2.5-1.5b/metal/pp512 | b11559→b11559 | +0.0% | +0.1% (10.0%, +++) | +0.0% (10.0%) | +49.8%/+49.8% | noise |
| qwen2.5-1.5b/metal/tg128 | b11559→b11559 | +0.0% | +0.8% (10.0%, +-+) | +0.1% (10.0%) | +74.4%/+74.6% | noise |
| tinyllama-1.1b/cpu/pp512 | b11559→b11559 | +0.0% | -0.2% (10.0%, -+-) | +1.1% (10.0%) | +39.4%/+41.0% | noise |
| tinyllama-1.1b/cpu/tg128 | b11559→b11559 | +0.0% | +0.0% (12.4%, -++) | +3.1% (16.3%) | +71.5%/+76.8% | noise |
| tinyllama-1.1b/metal/pp512 | b11559→b11559 | +0.0% | -0.2% (10.0%, ---) | +0.3% (10.0%) | +0.8%/+1.1% | noise |
| tinyllama-1.1b/metal/tg128 | b11559→b11559 | +0.0% | +0.1% (10.0%, -+-) | +0.7% (10.0%) | +54.1%/+55.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
