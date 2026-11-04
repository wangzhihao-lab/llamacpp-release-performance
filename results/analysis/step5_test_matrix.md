# Step 5: compact test matrix (set cover)

8 confirmed events: E01, E03, E04, E16, E19, E46, E49, E50. Events seen by each series (model/back end/test):

- mistral/cpu/pp512: 6 ['E01', 'E03', 'E04', 'E16', 'E19', 'E46']
- mistral/metal/pp512: 3 ['E01', 'E49', 'E50']
- tiny/cpu/pp512: 3 ['E03', 'E04', 'E19']
- tiny/metal/pp512: 3 ['E01', 'E49', 'E50']
- qwen/cpu/pp512: 2 ['E16', 'E19']
- qwen/metal/pp512: 2 ['E49', 'E50']
- mistral/cpu/tg128: 0 []
- mistral/metal/tg128: 0 []
- qwen/cpu/tg128: 0 []
- qwen/metal/tg128: 0 []
- tiny/cpu/tg128: 0 []
- tiny/metal/tg128: 0 []

Smallest number of series that see all detectable events: 2; there are 3 such sets:

- tiny/metal/pp512 + mistral/cpu/pp512
- qwen/metal/pp512 + mistral/cpu/pp512
- mistral/metal/pp512 + mistral/cpu/pp512

A single series sees at most 6 events (mistral/cpu/pp512) and misses at least 2.
