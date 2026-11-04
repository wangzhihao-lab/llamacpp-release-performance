# VE19: b3610 → b3665 (step-1 class V)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b3610→b3665 | +6.9% | +2.6% (20.3%, ++-) | +2.8% (10.0%) | +31.3%/+26.3% | noise |
| mistral-7b/metal/tg128 | b3610→b3665 | +5.6% | +5.8% (28.9%, +++) | +3.4% (10.0%) | +36.1%/+33.3% | noise |
| qwen2.5-1.5b/metal/pp512 | b3610→b3665 | -20.8% | +1.2% (24.8%, +-+) | +2.5% (10.7%) | +69.6%/+119.4% | noise |
| qwen2.5-1.5b/metal/tg128 | b3610→b3665 | +3.4% | -0.4% (16.7%, +-+) | +3.5% (10.0%) | +75.1%/+75.3% | noise |
| tinyllama-1.1b/metal/pp512 | b3610→b3665 | +5.8% | -0.1% (10.0%, --+) | -0.1% (10.0%) | +105.5%/+94.0% | noise |
| tinyllama-1.1b/metal/tg128 | b3610→b3665 | +0.9% | +0.2% (10.0%, ++-) | -0.5% (10.0%) | +57.1%/+54.9% | noise |

Omissions in the fixed configuration:

- A=b3610: --poll not supported and omitted (not equivalent)

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
