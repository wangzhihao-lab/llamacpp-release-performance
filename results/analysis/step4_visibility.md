# Step 4: visibility matrix of the confirmed events (thresholds of the v1.1 rule, two-sided)

Each cell: a visible change shows its percentage (newer release relative to the older one, fixed phase), · means measured but not visible, n/a means not applicable (for example the release does not support the model), and an empty cell means not measured. Data sources in order of preference: the dedicated re-tests of step 3b (the two cells T04 and T50) > the v1.2 re-measurements (E..R) > step 2 > the visibility re-measurements (V..).

| Event | tiny/metal/pp512 | tiny/metal/tg128 | qwen/metal/pp512 | qwen/metal/tg128 | mistral/metal/pp512 | mistral/metal/tg128 | tiny/cpu/pp512 | tiny/cpu/tg128 | qwen/cpu/pp512 | qwen/cpu/tg128 | mistral/cpu/pp512 | mistral/cpu/tg128 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E01 | **+159%** | · | n/a | n/a | **+47%** | · | · | · | n/a | n/a | **-22%** | · |
| E03 | · | · | n/a | n/a | · | · | **-65%** | · | n/a | n/a | **-68%** | · |
| E04 | · | · | n/a | n/a | · | · | **+195%** | · | n/a | n/a | **+185%** | · |
| E16 | · | · | · | · | · | · | · | · | **+24%** | · | **+23%** | · |
| E19 | · | · | · | · | · | · | **-41%** | · | **-40%** | · | **-24%** | · |
| E46 | · | · | · | · | · | · | · | · | · | · | **-23%** | · |
| E49 | **+90%** | · | **+81%** | · | **+59%** | · | · | · | · | · | · | · |
| E50 | **+37%** | · | **+33%** | · | **+30%** | · | · | · | · | · | · | · |

- E01: visible in 3 series
- E03: visible in 2 series
- E04: visible in 2 series
- E16: visible in 2 series
- E19: visible in 3 series
- E46: visible in 1 series
- E49: visible in 3 series
- E50: visible in 3 series
