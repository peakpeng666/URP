# Docker compiler-stage candidate v3

**Local review candidate, NOT RUN.** No Docker call, image pull, package installation,
native compilation, publication or hosted workflow dispatch was performed while
writing this candidate. Root reviews and authorizes any actual run separately.
This protocol is distinct from the rootless capability v7 experiment and cannot
establish that experiment's PASS.

## Narrow first-stage deliverable

`workflow/compiler-build.yml.example` is a manual-only, pinned-actions example,
not an installed workflow. It prepares an official Ubuntu 22.04 amd64 compiler
image with an authenticated package closure, then runs the retained compiler
plan offline under `urp.f2c.docker-engine-netnone/1`. Native build success writes
`built_not_accepted`, not scientific or deployment acceptance.

Selected application Git-blob provenance (not a full checkout): `3acf840d1a0c16ab1cfcca15744e4ea6609ddb35`.
Interpreter: CPython **3.12.13**, not the system Python 3.10 bootstrap interpreter.
F2C remains 2.1.0; OR-Tools remains 9.15.6755. Upstream source/interface pins are
in `preparation/inputs`. The retained compiler command body has an AST hash
regression and `build-plan-provenance.json`.

The base is the official amd64 platform manifest
`docker.io/library/ubuntu@sha256:98510ac07bb4545e389be502a8918b385c018bfe4ceeb5ac7e0375c782268b04`.
Existing metadata-only verification is retained in `evidence/`. Digest agreement
is content identity, **not a claim of a publisher signature**. Signed Ubuntu APT
snapshot provenance and setup-action/uv Python bootstrap provenance are separate
trust roots, explicitly recorded. See preparation documentation and receipts.

## Local review and later authorized launch

1. Review every candidate source file and run its pure fixtures. These fixtures
   do not invoke Docker, download software or run native scientific code.
2. After review/freeze, run `python3 freeze_source_index.py --root <candidate>`.
   Independently record the printed SHA256. The schema label `reviewed-source`
   is not self-authorization: the external reviewer must approve those bytes.
3. A future authorized workflow pins the candidate Git revision and this source
   index SHA, alongside the separate exact application revision above. The
   example assumes the candidate is stored at `ci/f2c-docker-candidate` in that
   future revision. Nothing has been published there by this work.
4. The workflow invokes `preparation/bootstrap_tools.py collect` after immutable
   setup-uv action, then `preparation/prepare_image.py` with explicit
   `--execute-trusted-preparation`. This networked, trusted stage authenticates
   packages and inputs; it does **not compile project native source**. It exports
   `/inputs`, immutable local image ID, provenance and a complete input index.
5. `engine_controller.py --execute-authorized-run --phase build` consumes that
   exact image ID and independently anchored input-index hash. It never pulls
   an image or repairs host settings. The example budgets a 5 GiB `/out` tmpfs,
   6 GiB memory limit, 2 CPUs, 512 processes and a 3600-second workload deadline.
   This is a finite candidate budget, not a promise compilation fits it.

The example has no automatic retry, cache publication, raw artifact upload,
release, deployment or PR trigger. Only a closed-vocabulary public receipt exposes finite stage outcomes, bounded
exit codes and approved hashes. **Private raw logs are ephemeral and not durably
archived; they disappear with the hosted runner.** Existing private collection
can preserve reviewed sources and the exposed receipt, not unavailable raw logs.
Store any still-accessible evidence privately. Export failures
retain a bounded partial tar when possible and explicit failure records. If the
container was killed before export, vanished tmpfs evidence is reported as
missing rather than fabricated. Cleanup is restricted to the exact new container.

## Isolation identity and trust boundary

The trusted host controller uses only the local Docker engine with an empty
private client config and an allowlisted environment. The workload has no
credentials or Docker socket. It uses the engine-created network-none namespace,
non-root numeric UID/GID, no capabilities, default seccomp, no-new-privileges,
read-only root and inputs, private IPC/cgroup namespace, bounded tmpfs output and
bounded daemon logs. No privileged mode, host network, seccomp-unconfined,
nested-unshare exemption or persistent host security changes are used.

A live entrypoint is held while the controller cross-checks immutable image and
container policy, host PID/start time, kernel net namespace, boot identity and
inside FD/capability/route observations. It stays live through bounded evidence
export. Failure to inspect the live host PID, PID reuse, unexpected mounts,
external routes or unsupported defaults fails closed. The old rootless namespace
receipt is neither reused nor relabeled.

## Explicitly pending acceptance

A compiler-stage zero exit establishes compilation only. A separate runtime image
must be prepared from the same official base with its own authenticated runtime
package closure, without compiler/build-tree dependencies. It must then pass
fresh relocated-venv imports, ELF ABI/GLIBC/RUNPATH/strong-symbol closure, actual
both-order provider mapping, independent geometry and checker evidence, and the
full **current application** suite plus frontend contracts. The runtime adapter is separately reviewable but not first-stage acceptance.
The compiler source index deliberately excludes the pending `validation/` and
`preparation/runtime/` subtrees; they require a later separate freeze/review.

Current application collection/results must be measured afresh. The historical
185 application's 602 testcase elements and 17 additional subtests (619 reported
suite tests) are historical only, not a required or inferred current count.
Any eventual portability statement is scoped to the tested Jammy runtime,
not universal Linux, ROS, physical safety, deterministic timing or bit-identical
build reproducibility.

## Review revision 4

This revision preserves the separate immutable revision-3 snapshot and fixes its
review findings. The controller rejects every unsupported input node using
`lstat`, including mocked FIFO/socket/device cases, and rejects writable input
directories. The independent workflow bootstrap uses explicit checks that remain
active under optimized Python. Missing result evidence or public projection
failure now forces a nonzero workflow result, even after a zero build exit.
Pure tests exercise the actual inline bootstrap and EXIT trap; they do not create
special files, run Docker, install packages or compile native code.

The source-indexed manual workflow remains a review template. A separately
rendered fixed-pin push wrapper is needed for a newly introduced workflow on a
repair branch. Its source and index pins are selected at review/render time, not
by workflow inputs. Root retains publication and execution authority. The
rendered wrapper must live outside this source-indexed tree to avoid a circular
source hash. No compilation, runtime validation or deployment acceptance has yet
been established by these local tests.

## Review revision 5

Revision 5 keeps the immutable v4 snapshot and corrects preparation reads that
mistook access-time updates for source mutation. `prepare_image.read_file` and
`bootstrap_tools.collect` compare device, inode, mode, link count, owner/group,
size, mtime_ns and ctime_ns explicitly; atime is intentionally excluded. Source
anchors, digest rereads, size/type and symlink/hardlink checks remain active.
Owned-file and controlled-stat tests cover atime-only reads, each stable field,
content replacement, inode replacement and post-read symlink substitution. The
UV version command is mocked in these fixtures; no native tool is executed.

The public preparation failure detail is an exact small JSON projection: a fixed
preparation stage, allowlisted invariant code and allowlisted exception class.
Unknown errors receive a fixed generic code. The receipt reader rejects aliases,
oversized input, duplicate keys, extra fields and free text. It does not scan or
publish Docker logs, commands, paths, URLs, headers or environment values. Nested
SAFE_PACKAGE_DIAGNOSTIC extraction is deliberately not implemented in this
revision; image-build failures identify their top-level stage/class only. Raw
logs remain ephemeral, not durably archived.
