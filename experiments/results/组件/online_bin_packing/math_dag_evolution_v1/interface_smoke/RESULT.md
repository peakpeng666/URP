# Fixed-DAG JSON-schema interface smoke: rejected before generation

Exactly one separately specified non-scored HTTP request was sent. The frozen schema, target, prompt, seed and limits were not changed, and there was no retry. No DAG interpreter, packing/fitness evaluation or formal candidate generation occurred.

## Recorded outcome

- Start2026-10-04T19:23:30.965175+00:00; server exit2026-10-04T19:23:31.733670+00:00
- Whole lifecycle0.767954s; ready0.616669s; request0.001676s
- HTTP400, complete221-byte response, matching Content-Length
- Exact error: JSON schema conversion failed at `#/properties/nodes/items/anyOf/0/items`: schema must be an object
- This field is the boolean `items:false` in a fixed-length tuple schema. The error is an interface/schema-expression compatibility failure, not a model algorithm-quality result
- No model content, effective grammar, EOS or generated token count was returned. Do not manufacture empty model content, an EOS result or throughput from this rejected request
- Server exit0 after requested SIGTERM; direct child reaped; HTTP writer finished. Exit0 alone did not make the smoke pass: assessment.passed=false
- Kernel child peakRSS2,863,644,672 bytes; userCPU0.694256s; systemCPU0.144187s. Same4GiB virtual-address hard cap,4GiB sampled RSS threshold,2 model threads and120s lifecycle budget
- Shared model/runtime/source hashes match before and after. Frozen CVRP files were not modified

The measured request had86 inputtokens,128 requested outputtokens and a known target whose text tokenizes to46tokens withoutEOS. The original embedded non-thinking template/rendered bytes are identified by freeze.json; historical relative template-path wording in protocol.json is metadata, not the file resolution used. No benchmark/design/validation data was included.

## Evidence

- Scientific input freezeSHA: bfe195ff3c8d9de97be0b0ca68aa0f06ad4db05d2011505391dad3e113776b77
- Exact requestSHA: 3e78cf0384795caf55a43684554a8dc9c494a76f7fa5557831b641ee81f70807
- Raw HTTPbodySHA:29c7b5ef23047cd1c3beeb5a96561212b2b1df36d20ea617d1b3d46670053438
- runs/attempt01/response_body.json, response_metadata.json, result.json, assessment.json, run_freeze.json, server_stderr.log and server_stdout.log

No schema edit or second request follows this failure. Any equivalent schema-expression adaptation must be a separate version with a new pre-run specification, keeping this failure and its original schema intact. This smoke cannot establish complete grammar enforcement or later strict DAG admission, even if a future fixed-data transcription succeeds.
