# E08: b1939 → b2060 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b1939→b2060 | -40.7% | -8.3% (66.3%, ---) | +2.5% (19.4%) | -33.6%/+14.8% | noise |
| mistral-7b/metal/tg128 | b1939→b2060 | -32.6% | -9.9% (49.7%, --+) | +1.1% (10.0%) | -27.4%/+8.9% | noise |
| qwen2.5-1.5b/cpu/pp512 (not listed) | b1939→b2060 | +27.7% | +11.2% (15.2%, +++) | +13.0% (25.8%) | +8.9%/-3.7% | info |
| qwen2.5-1.5b/cpu/tg128 | b1939→b2060 | -16.7% | +0.8% (12.4%, +++) | -5.7% (44.1%) | +2.0%/+15.5% | noise |
| qwen2.5-1.5b/metal/pp512 | b1939→b2060 | +77.1% | -0.2% (32.2%, --+) | +3.9% (54.5%) | +26.1%/-26.0% | noise |
| qwen2.5-1.5b/metal/tg128 (not listed) | b1939→b2060 | -2.5% | +0.6% (23.2%, -++) | +5.9% (33.7%) | +45.3%/+57.8% | info |

Omissions in the fixed configuration:

- A=b1939: mmap not supported and omitted (equivalent: models load through mmap by default)

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
