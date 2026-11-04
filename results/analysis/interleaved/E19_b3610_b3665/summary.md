# E19: b3610 → b3665 (step-1 class A)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b3610→b3665 | -17.1% | -24.7% (17.6%, ---) | -19.7% (10.0%) | +36.5%/+32.3% | C |
| mistral-7b/cpu/tg128 (not listed) | b3610→b3665 | -0.2% | -6.5% (17.3%, ---) | +0.3% (10.0%) | +59.0%/+59.7% | info |
| qwen2.5-1.5b/cpu/pp512 | b3610→b3665 | -33.1% | -40.2% (10.0%, ---) | -40.6% (10.0%) | +52.9%/+35.6% | C |
| qwen2.5-1.5b/cpu/tg128 (not listed) | b3610→b3665 | +1.9% | +2.2% (14.3%, +-+) | +10.4% (10.0%) | +64.9%/+78.8% | info |
| tinyllama-1.1b/cpu/pp512 | b3610→b3665 | -38.2% | -40.7% (10.0%, ---) | -42.1% (10.0%) | +38.8%/+30.1% | C |
| tinyllama-1.1b/cpu/tg128 (not listed) | b3610→b3665 | -13.2% | -0.9% (10.0%, ---) | +1.9% (10.0%) | +99.7%/+134.3% | info |

Omissions in the fixed configuration:

- A=b3610: --poll not supported and omitted (not equivalent)

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
