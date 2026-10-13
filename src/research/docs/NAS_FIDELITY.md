# NAS训练保真度模块

恢复、核验和重算已有NAS实验。完整包位于[训练保真度与独立重训](../../../experiments/results/优化与训练/训练保真度与独立重训/)，本机测试见[检查记录](../../checks.json)。

## Scope and defaults

- `python scripts/test.py` and `python scripts/urp.py smoke` still use only the standard library. The latter still runs the same three historical synthetic examples.
- `nas sources`, `nas restore`, `nas import-data`, and `nas verify` need no PyTorch or NumPy.
- There are no automatic downloads, dependency installs, external model calls or training. No URL argument is accepted as a local archive.
- `nas smoke` explicitly opts into eight small synthetic CNN forward checks, two synthetic samples each. It does not use CIFAR, call an optimizer or produce a scientific score.
- `nas recheck` recomputes frozen statistics; `--checkpoints all` additionally runs all 160 frozen endpoints on the same 1,000 validation samples. Neither trains a model.
- `nas train` is disabled unless `--execute-training` is supplied. It creates a new run with the unchanged 80-trajectory / 1,600-epoch protocol, rather than appending scores to the historical evidence. This command was not executed for this integration.

The twelve Python files under `src/urp_research/nas_fidelity/frozen/` are byte-identical to the published research archive, including its independent audit and tests. `configs/nas_fidelity.json` pins every archive member and all twelve sources. The wrapper changes paths and output placement around those files, not their formulas, training recipe or selection logic.

## Recover the exact evidence

Use the three files in the [NAS Drive delivery](https://drive.google.com/drive/folders/1REkWhOogD2FtnuG80QDj66soVD3JM5j5). Download them through your own authorized Drive account. The software does not sign in, download, upload, or change sharing permissions.

| Local argument | Drive file ID | Bytes | SHA-256 |
|---|---|---:|---|
| `--code-zip` | `1pP9hV6fTSV7juRhppanl9Ax7ezNGcklQ` | 9,553,403 | `1e429814b58b86df05e486d07f127caa9b15b962dcc9275963b6ab241edff3f7` |
| `--discovery-zip` | `1cGEeJ24LfXHudGXMTCSfTF4ntESiK5wV` | 24,732,887 | `6e048bb75951c3837c7d9d0440533248a5eadbd783cbf6f3317c83b3629c1e4b` |
| `--confirm-zip` | `1Rj4g2qdx0fVqadMn2rYX-opMOq97oOLu` | 24,727,814 | `818dba0f21259caaa7c81f9780d4caa7de74a0b8c29c9570a48976a1120d8a89` |

Identities come from the successful Drive readback receipt at 2026-10-06 05:44:32 UTC. The three ZIPs contain 683 disjoint members, including the delivery manifest itself. The inner delivery manifest lists the other 682 files. The code archive contains logs, configuration, source, reports, and the complete 124-file older P4 reference snapshot. Discovery and confirmation weights contain 120 files each: 80 fixed-endpoint states and 40 recovery states per group. None of these runtime artifacts is included in the source package.

From this source directory:

```sh
python scripts/urp.py nas sources
python scripts/urp.py nas restore \
  --code-zip /path/P4_报告代码与原始日志_20261006.zip \
  --discovery-zip /path/P4_发现组权重_20261006.zip \
  --confirm-zip /path/P4_独立重训权重_20261006.zip \
  --output data/nas-fidelity
python scripts/urp.py nas verify --root data/nas-fidelity
```

All three archives are mandatory. Restoration checks archive bytes/SHA-256, rejects symlinks, traversal and duplicate ZIP names, verifies every member, and publishes only a complete new destination. Existing destinations are refused. No archived script is executed by restoration. Later verification rejects extra files or changed bytes, including missing or substituted checkpoints.

## Import official CIFAR binary data locally

The research archives deliberately exclude the dataset. Obtain the original archive from the manifest's [official CIFAR binary URL](https://cave.cs.toronto.edu/kriz/cifar-10-binary.tar.gz). The reference [CIFAR page](https://www.cs.toronto.edu/~kriz/cifar.html) describes the dataset. Downloading remains a separate explicit user action.

Pinned archive:

- Filename: `cifar-10-binary.tar.gz`, 170,052,171 bytes
- SHA-256: `c4a38c50a1bc5f3a1c5537f2155ab9d68f9f25eb1ed8d9ddda3db29a59bca1dd`
- MD5: `c32a1d4ab5d03f1284b67883e8d87530`

```sh
python scripts/urp.py nas import-data \
  --archive /path/cifar-10-binary.tar.gz --output data/cifar-training
python scripts/urp.py nas verify --root data/nas-fidelity --data data/cifar-training
```

Only `data_batch_1.bin` through `data_batch_5.bin` are extracted. Each must be exactly 10,000 × 3,073 bytes and match the original per-batch SHA-256. This is the binary format, not the Python/pickle dataset. No `extractall` or pickle loader is used by the integration. The original split is byte-pinned to SHA-256 `8ad2ccf80dfd3a0b175a24ca0941ff8169da2a055fd9602bb9b0660a357b362a`: 4,000 train, 1,000 validation, and 45,000 reserved indices, disjoint and covering the five training batches.

The compressed official archive also contains test data. Its complete compressed bytes are hashed for integrity, but the test member is never extracted, parsed as samples or evaluated. Validation in this study is not an independent test set.

## Optional exact CPU environment

Use a separate CPython 3.12 environment. The base project stays dependency-free. The actual historical and local engineering checks used NumPy 2.5.3 and CPU PyTorch 2.14.1+cpu. The optional entry points fail closed on a different version. They do not install anything themselves.

```sh
python -m venv .venv-nas
.venv-nas/bin/python -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
.venv-nas/bin/python -m pip install numpy==2.5.3
.venv-nas/bin/python scripts/urp.py nas smoke
```

The full historical environment lock remains in the restored research evidence. The two direct optional requirements are listed in `configs/nas_requirements.txt`; this is not a claim that a clean-machine dependency installation has been independently tested. Windows and cross-hardware bitwise identity are not certified. Formal new training uses the original Unix `resource` module. Do not run Python with `-O` or `-OO`; frozen research checks rely on assertions.

## Recheck the existing result

```sh
.venv-nas/bin/python scripts/urp.py nas recheck \
  --root data/nas-fidelity --data data/cifar-training \
  --output outputs/nas-recheck-001 --checkpoints all
```

Omit `--checkpoints all` to skip checkpoint inference while retaining structural, frozen-hash, original-model-construction, statistic and cost checks. The default is `none`, not a partial scored experiment. Both modes require the exact recovered data.

The wrapper creates independent copies under the new output directory. It recreates the old P4 fence in that copy, verifies copied bytes immediately before dynamic imports or loading states, then calls the unchanged independent audit. Full mode uses a separately implemented CNN and batch size 73 to verify every frozen prediction, correct count, loss, checkpoint identity and Adam step count. Loading uses only fixed-hash trusted historical checkpoints with `torch.load(..., map_location="cpu", weights_only=True)`; this is not a general service for arbitrary `.pt` files. Restricted loading is an additional safeguard, not a promise that untrusted weights are universally safe.

The unchanged analysis is then rerun on the copy. The entire summary must equal the frozen one except its generation timestamp; both CSV outputs must be byte-identical. Ten thousand seeded block-bootstrap samples preserve joint architecture dependence within each group, shared discovery resamples for the 2/20 endpoints, independent confirmation resamples, and fixed original top-1 choices.

Outputs:

- `independent_audit.json`: original independent audit report
- `engineering_recheck.json`: concise engineering verification receipt
- `work/experiment/reports/`: regenerated summary and CSVs
- `work/`: retained independent evidence copies, deliberately outside the source package

Plan roughly 0.5 GB of disk for restored evidence, imported batches and a full recheck copy. Every run requires a new output path. Failure retains the diagnostic copy; neither the original evidence nor its logs are reused for writes.

## Deliberately start a new reproduction

This is a costly optional action and was not performed by the engineering check:

```sh
.venv-nas/bin/python scripts/urp.py nas train \
  --root data/nas-fidelity --archive /path/cifar-10-binary.tar.gz \
  --output outputs/nas-new-reproduction-001 --execute-training
```

Without that last flag the command fails before reading evidence, importing optional packages, creating outputs or running subprocesses. With it, the wrapper uses a fresh output only and follows the original workflow: verified training-only extraction → non-scoring synthetic timing and parity/recovery tests → fresh pre-run freeze → independent preflight → all discovery trajectories → frozen selections → all confirmation trajectories → analysis and independent endpoint audit. No seed, architecture, endpoint, optimizer, augmentation or budget is changed. Confirmation can start only after all discovery results exist and the selection receipt and hashes verify. The original runner enforces this order.

Fixed recipe: eight architectures, five discovery seeds 310001–310005, five disjoint confirmation seeds 320001–320005, 2/20 nested endpoints, batch 128, Adam learning rate .003 and weight decay .0001, pixels /255, no augmentation, one CPU thread, fixed run-order seed 20261006. Twenty epochs is a larger fixed budget, not proven convergence. Earlier execution took about 36.6 CPU minutes for training; this is historical evidence, not a time guarantee.

New execution is clearly recorded by `execution_intent.json` and a fresh freeze. Historical authorization strings inside the unchanged script are provenance, not permission to start work. Interrupted runs retain all attempt and epoch journals. The wrapper intentionally offers no implicit restart or overwrite. Advanced recovery uses only the original runner's explicit `--resume` inside that same new experiment directory, after verifying the failed attempt and checkpoint/journal consistency; partial-epoch costs remain unknown rather than zero. Never delete failure logs, change seeds or recreate runs to select favorable results.

## Research boundary

The completed study's five-seed mean selects `d3_w16_k5` at both endpoints and obtains 40.92% confirmation validation accuracy with zero empirical regret within this eight-architecture comparison. Two of five individual short-training seeds select a different structure; this prevents treating one short run as a reliable ranking. This is a within-P4 fixed-architecture fidelity diagnostic, not a controller comparison, weight-sharing method, whole-paper reproduction, independent-test result, proof of convergence or general NAS guarantee.

See the [original result report](https://drive.google.com/file/d/1FJ47kgwZFrTxvQ9u1VMBt57dX1rPKI3-/view). The Git source package contains only engineering code, tests, source/hash manifests and documentation. Data, weights, raw logs, extracted papers, figures, private keys and credentials are excluded. Existing Drive permissions are unchanged. The candidate version is `0.2.0rc1`; final metadata-diff verification and publication remain pending.
