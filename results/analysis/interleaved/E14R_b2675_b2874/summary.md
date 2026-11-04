# E14R: b2675 → b2874 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b2675→b2761 | +77.8% | +0.0% (10.0%, +++) | +0.1% (10.0%) | +114.7%/+20.8% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b2675→b2761 | +9.0% | +0.2% (10.0%, +++) | +0.4% (10.0%) | +61.3%/+48.5% | info |
| qwen2.5-1.5b/cpu/pp512 | b2675→b2874 | -16.5% | +0.2% (26.2%, -++) | +11.4% (13.2%) | +20.6%/+60.9% | noise |
| qwen2.5-1.5b/cpu/tg128 | b2675→b2874 | -25.1% | -4.2% (34.1%, -++) | +9.9% (10.0%) | +32.8%/+94.8% | noise |
| qwen2.5-1.5b/metal/pp512 | b2675→b2874 | -50.3% | -2.0% (22.8%, +--) | -1.9% (22.0%) | +3.4%/+104.0% | noise |
| qwen2.5-1.5b/metal/tg128 (not listed) | b2675→b2874 | +13.4% | +0.5% (10.0%, +-+) | +0.7% (10.0%) | +94.6%/+72.8% | info |
| mistral-7b/cpu/pp512 | b2761→b2874 | -11.2% | +1.2% (10.0%, -++) | -0.1% (10.0%) | +28.3%/+44.4% | noise |
| mistral-7b/cpu/tg128 (not listed) | b2761→b2874 | -7.7% | +0.7% (10.0%, ++-) | +0.3% (10.0%) | +30.9%/+42.2% | info |
| tinyllama-1.1b/cpu/pp512 | b2761→b2874 | +28.5% | +3.6% (20.4%, +++) | +1.0% (21.2%) | +55.1%/+21.9% | noise |
| tinyllama-1.1b/cpu/tg128 | b2761→b2874 | +38.3% | +2.4% (20.8%, +-+) | +5.6% (10.0%) | +95.9%/+49.6% | noise |
| tinyllama-1.1b/metal/pp512 | b2761→b2874 | -43.0% | -6.3% (10.0%, ---) | -6.6% (10.0%) | +20.6%/+97.5% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b2761→b2874 | -0.9% | -0.4% (10.0%, ---) | -0.3% (10.0%) | +48.5%/+49.5% | info |

Omissions in the fixed configuration:

- A=b2675: -fa not supported and omitted (equivalent: this release has no flash attention)
- A=b2675: -pg not supported and omitted (equivalent: this release has no combined -pg test)
- A=b2761: -fa not supported and omitted (equivalent: this release has no flash attention)
- A=b2761: -pg not supported and omitted (equivalent: this release has no combined -pg test)

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
