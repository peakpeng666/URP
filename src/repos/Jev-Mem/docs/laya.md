# Jev-Mem with Laya

Laya is an optional local System-One decision model. It replaces the Jev API
for memory typing, relation decisions, query routing, candidate scoring, and
stopping. Memory storage, retrieval policies, and System-Two answer generation
remain shared with the Jev backend. Jev stays the default.

## Install and run

Use Python 3.11+ from the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install '.[laya]'
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env` for answers and evaluation. For Azure OpenAI v1
or another compatible endpoint, also set `OPENAI_BASE_URL` and choose the chat
deployment with `--model`. `TYPESAFE_API_KEY` is not needed in Laya mode. The
TypeSafe SDK supplies shared question/answer types; local decisions do not call
the TypeSafe API. Existing environment variables take precedence over `.env`.

```bash
USE_TF=0 python -m jev_mem.benchmarks.locomo \
  --dataset examples/locomo_synthetic.json \
  --jev-config config/laya_mem.json \
  --sample 0 --max-questions 2 --best-of-n 1 --no-parallel \
  --model gpt-4o-mini
```

This checks the complete path on three synthetic turns and two questions.
It is not a benchmark of answer quality. For LoCoMo, use your downloaded dataset
instead; see the [data guide](../data/README.md). The same profile works with
`python -m jev_mem` and `python -m jev_mem.benchmarks.longmemeval`.

On Windows, activate with `.venv\Scripts\Activate.ps1`, set `$env:USE_TF="0"`,
and run the Python command without the `USE_TF=0` prefix. `USE_TF=0` avoids
unnecessary TensorFlow imports in environments where it is installed.

### Apple Silicon / MLX

On Apple Silicon with macOS 14+, install and select the MLX runtime:

```bash
python -m pip install '.[mlx]'
USE_TF=0 python -m jev_mem.benchmarks.locomo \
  --dataset examples/locomo_synthetic.json \
  --jev-config config/laya_mlx_mem.json \
  --sample 0 --max-questions 2 --best-of-n 1 --no-parallel \
  --model gpt-4o-mini
```

The profile uses `aac6fef/laya-mlx` on the GPU. MLX also accepts `cpu` or `auto`.
The project still uses PyTorch for its embedding models. The MLX extra is only
installed on supported Apple Silicon platforms.

## Runtime and configuration

- PyTorch defaults to CPU on macOS and automatic accelerator selection elsewhere.
  Set `laya_device` explicitly when needed, for example `cpu` or `cuda`.
- `laya_model` accepts a Hugging Face model ID or local checkpoint directory;
  `laya_subfolder` optionally selects a bundled checkpoint. This integration uses
  the direct SDK, without automatic model routing.
- Weights download on first use. Local decisions can then use cached weights;
  final answers and judging still use the configured provider.
- `laya_batch_size` bounds the number of questions per forward pass. Calls are
  serialized per client. Concurrent retrievals queue before their retrieval
  deadline starts; queue time is reported separately.
- macOS defaults `OMP_NUM_THREADS` and `MKL_NUM_THREADS` to `1` before native
  imports and runs PyTorch embeddings on CPU. Explicit thread settings are preserved.
- Supplied Laya profiles use a 600-second decision timeout and 1800-second
  retrieval budget, with `fallback_to_magma: false`. Inference failures are raised
  instead of silently switching controllers. Model loading occurs before these
  budgets. A running forward pass cannot be interrupted; late results are rejected.

## Cache reuse

Backend settings participate in automatically generated cache fingerprints.
Switching between Jev, Laya and Laya-MLX creates a separate graph cache.
`--reuse-memory` also checks the backend, Laya model, and subfolder; using another
backend's graph requires rebuilding. Historical caches without backend fields
are treated as Jev caches. The Python memory-loading API applies the same backend
check before loading a graph.

You can explicitly reuse a matching LoCoMo graph while adjusting retrieval or
timing settings. Use the exact directory containing `graph.json`, `vectors/`,
`keyword_index.json`, and `jev_mem_config.json`. Treat a changed local checkpoint
or updated remote weights as a new model and rebuild; model IDs alone do not
identify a weight revision.

## Evaluation limits

The README's paper results use Jev and do not establish Laya's performance.
The default English Laya checkpoint has a 512-token context; its SDK truncates
long states, which may omit evidence in decisions over multiple candidates.
Jev's thresholds may need recalibration for Laya. Record the backend, checkpoint,
runtime, configuration and dataset when measuring accuracy or speed.

References: [Laya model card](https://huggingface.co/convaiinnovations/laya),
[Laya SDK](https://github.com/NandhaKishorM/laya),
[Laya-MLX runtime](https://github.com/mizorewww/laya-mlx).
