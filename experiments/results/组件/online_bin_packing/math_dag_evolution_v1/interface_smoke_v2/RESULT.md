# Fixed-target DAG schema v2 interface smoke

One non-scored request completed successfully. The v1 schema-conversion HTTP400 remains preserved separately. This result demonstrates this fixed target's acceptance and observed constrained output, not all schema restrictions or algorithm-design quality.

- Approved freeze: `635487393091b3734e714e4305aadd01ca0acdd76ec2774b34185961550c5ba3`
- Request: `e82fed561c546b253712059dc36b7ca85b63254222f0424c0a2b610056d42c3e`
- Schema v2: `90e2d6d2c1c4803d788b23c8b4cc703f5907c4d040f490dd0243ab3f847e7f2d`
- Actual start: 2026-10-04T19:48:14.686967+00:00; finish: 2026-10-04T19:48:21.702762+00:00
- Whole process lifecycle: 7.015132s; readiness: 0.613481s; request: 6.335696s
- Runtime prompt evaluation: 1881.896ms; generation: 4449.542ms
- HTTP200; 86 prompt tokens; 47 output tokens including EOS151645; stop_type=eos; truncated=false
- Strict complete content equals the handwritten target by JSON value; raw content retained without repair
- Effective grammar SHA: `e936cbe6ad9fbcd7d6499957c805f74b68f27caba745a3877dd38b4ee511d6fd`; no incomplete-conversion warning
- Raw HTTP body SHA: `1b6a79bacecf34c854dc1242eda03b81c3c2b7925faf4844db72ee920cb0110f`; content SHA: `aeaaabb0e8465ea5c93302845aa6b015302a1f0b12d481ddf1a08d6cff1bbedc`
- Peak sampled RSS: 2877538304 bytes; ru_maxrss: 2877124608 bytes
- Limits unchanged: 4GiB hard address-space limit, sampled 4GiB RSS threshold (not hard RSS isolation),120s lifecycle,2 model threads,ctx2048,cap128
- Server exit0 after requested SIGTERM; direct child reaped; HTTP writer finished
- Full frozen sources/assets verified before and after; one POST; graph interpreter, fitness and formal candidate calls all zero
- cache_n=0; tokens_cached=132 records current slot KV occupancy, not cross-request cache reuse. Fresh process does not imply an operating-system page-cache cold start

The protocol retains official Qwen/Qwen3-4B-GGUF Q4_K_M at revision bc640142c66e1fdd12af0bd68f40445458f3869b and llama.cpp b11387 commit8330e9696708fcfd5d465cdbd333e4c5a67e2808. GGUF embedded name “Qwen3 4B Instruct Awq” remains an unresolved label discrepancy. It is not the original paper's GPT3.5 model. Non-thinking rendered input and exact token IDs were copied unchanged from v1. The result.json freeze_sha256 field hashes run_freeze.json, distinct from the approved top-level freeze above.

The unchanged DAG validator remains authoritative for later candidate admission. No22-request experiment is authorized by this smoke.
