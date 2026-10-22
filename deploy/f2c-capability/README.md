# Jammy rootless capability candidate v5

This is a separate, diagnostic-only cohort. It does not build or import Fields2Cover, prepare a root filesystem, install packages, modify the host APT database, add subordinate-ID allocations, install setuid programs, change host security settings, or publish artifacts/caches. A successful result is a capability proof, not a scientific/native validation result.

## Preserved hosted v1 result and diagnostic scope

Hosted capability v1 run `39815381470`, job `119952469283`, at commit `f17b6bb1eeca864be42265938faa692644111854` passed its anchor and helper-test stage using Python 3.10. The retained source/index-only review counted 165 fixtures; detailed hosted test output was suppressed, so the hosted fixture count was not independently observed. Authentication then failed with `CAP_MODE_REJECTED`; namespace proof was skipped. No rootfs or native build occurred. The failed object and predicate were not reported and remain unknown.

V2 adds only finite `subject` and `check` labels to authentication mode-failure receipts and their verified projection. All ownership, write-bit, alias, type, size, executable and setuid rejection predicates remain intact. Labels come from reviewed static categories, never runtime paths, usernames, UID/mode values or exception text. Malformed or unknown diagnostic combinations project `UNKNOWN`.

The exact official runner-image source applies `chmod -R 777 /usr/share` late in provisioning. That conflicts with the protected-ancestor requirement for the configured Ubuntu keyring if the state persists; a mocked fixture reproduces that rejection without opening any file. It is not evidence that this was the failed object in the hosted run. V2 does not change modes, bypass checks, substitute a keyring or introduce a new trust source.

## V4: authenticated public-keyring data input

The subsequent hosted capability run `39821091519`, job `119972238938`, at commit `989f6a654d17b7d8633f87428e3431e555667329` passed anchor and helper stages, then reported `stage=authentication status=FAIL code=CAP_MODE_REJECTED subject=ARCHIVE_KEYRING check=COMPONENT_WRITABLE`. Namespace proof did not run. This establishes only the first rejected input, not success of any later facility.

V4 replaces reliance on the unused writable host public-keyring file with a separately source-anchored public-data input. The exact unmodified Canonical download is 3,607 bytes, SHA256 `80a36b0a6de2f69f49d2df75ef473ccde121e9e190b9ea01d20a4f63778d5c31`. The independently documented direct signer remains `F6ECB3762474EDA9D21B7022871920D1991BC93C`. Public packet inspection proves the inventory and fingerprint, not cryptographic signature validity; the future hosted verifier must still validate each frozen InRelease signature.

The reviewed bytes are copied into a fresh private data input and consumed through a held, fully sealed memory-file descriptor. Only the exact internally generated descriptor path is accepted by the verifier command; no default or extra keyring is permitted. The descriptor is closed before later authentication/helper work. Lock schema 2 and protocol `private-public-keyring-v1` distinguish this data trust anchor from authenticated installed-package files. The old host keyring is neither repaired nor described as authenticated. All other executable, runtime, control-file, metadata/package, NSS, helper and namespace predicates remain enforced. No general writable-path exception or host permission change is introduced.

This is a new trust-input protocol, not a claim that v1 or v3 passed. Its externally reviewed source-index anchor is independent of the Ubuntu metadata/package chain it authenticates; downloading a key and its checksum together at runtime would not provide that guarantee. Initial platform, interpreter and verifier trust remains explicit. A successful capability proof would still not authorize or establish a rootfs/native build.

## V5: explicit signed ownership for canonical package hops

Hosted v4 run `39825742401`, job `119988438351`, at commit `4d9a23b04b7e11c40b0b826bc7d04a78fc1a5fdc` passed anchor and helper stages, then failed authentication with `CAP_BYTES_REJECTED`; namespace proof was skipped. This generic code does not identify the failed host object or establish corruption. The published public-keyring bytes were independently read back unchanged.

A separate pure reproduction using exact official Jammy archives demonstrates a real verifier defect: `libpython3.10-stdlib` owns `/usr/lib/python3.10/_sysconfigdata__linux_x86_64-linux-gnu.py`, a symlink to `_sysconfigdata__x86_64-linux-gnu.py`, while `libpython3.10-minimal` owns the regular target. Both packages are version `3.10.12-1~22.04.18`. V4 incorrectly required the regular target to be present in the alias owner's archive. This is proof of rejection of a valid canonical package layout, not observation of the unreported hosted failed path.

V5 attributes each non-usrmerge symlink hop and the terminal regular member to a unique actual owner whose exact installed identity and archive are authenticated against the signed snapshot. It does not union unrelated archives, infer ownership from filenames, or skip alias targets or byte/size/mode/UID/GID requirements. The four existing root usrmerge aliases retain their exact fixed layout policy; that policy is recorded separately and is not represented as a signed package-owned symlink. Lock schema 3 and the explicit package-member attribution protocol distinguish this provenance from v4. Public-keyring sealing, host controls, NSS and namespace gates are unchanged. No rootfs or Docker protocol is introduced.

## Why this candidate exists

The preceding Jammy v7 workflow passed its hermetic helper fixtures, then refused a downgrade during signed package closure verification. Hosted run `39800731973`, job `119900349167`, identified the authenticated target `libpq-dev`, `14.24-0ubuntu0.22.04.1`, `amd64`, snapshot `20261021T000000Z`, `jammy-updates/main`, stanza `1632`. It did not disclose or authenticate the preinstalled version. Preserve that result; this candidate does not replace it with a synthetic diagnosis.

The exact official runner-image source installs unpinned `libpq-dev` through PGDG and then removes the repository/key. That supports a mismatch mechanism but is not proof of the private installed version. Adding a PGDG provenance policy would require an independently reviewed key, frozen signed records, exact archive and runtime dependency verification, and a new identity. Accepting an unknown newer host package or permitting a downgrade is not allowed.

The preferred alternative is a future clean authenticated Jammy root filesystem on the same standard runner, conditional on this probe. Existing image source includes Podman, but neither usable subordinate allocations nor bubblewrap availability is established by the software inventory. This probe does not assume or silently install them.

## Bounded proof

1. Authenticate the relevant existing system tools and native runtime against official signed Jammy metadata; record private measured inputs. Bootstrap system Python and metadata-verification utilities are an explicit trust boundary, not retroactively claimed to have been authenticated before first use.
2. Read, but never edit, the current user's existing subordinate UID/GID allocations and relevant files/NSS configuration. Missing or insufficient allocation is terminal. Do not flatten ownership or create mappings outside an existing grant.
3. Keep a direct trusted child live and unreaped while authenticated existing uidmap helpers establish only ephemeral kernel namespace mappings. The Jammy helper version accepts numeric PIDs, so identity/liveness is checked with a pidfd and retained proc-directory identity.
4. Prove a private mount namespace and fixed nonzero ownership on a bounded, namespace-local tmpfs. No host-owned file is chowned. Namespace teardown removes the mount; only the empty private mountpoint is removed by the parent.
5. Prove the composition needed by a later offline build: outer multi-ID user/private mount context followed by a fresh inner root-only user/network namespace. Preserve loopback-down, no external interface/route, no inherited socket, boot and namespace-identity checks.
6. Bind the comparison to an actual host-opened network-namespace FD, checked with the kernel namespace-type ioctl and device/inode identity. Environment text is not proof. Close that FD after the trusted guard; no arbitrary build payload is run by this candidate.
7. Recheck measured inputs and clean up the trusted child and ephemeral fixture. Any unsupported capability, altered input, timeout or invalid receipt is terminal, without a fallback mode.

The supported NSS policy is deliberately narrow: `passwd` and `group` use only `files`, or `files systemd`; a permitted systemd fallback must be authenticated with its required ELF closure even when normal lookups remain local. Literal subordinate-owner names must resolve uniquely in measured local passwd data. Numeric or unknown owner forms are rejected as unsupported, not declared invalid operating-system allocations. Raw inherited login-UID checks and repeated nscd endpoint-absence checks bound the helper lookup paths. These are measured process/runtime guarantees, not authentication of the whole host or remote daemons.

A future rootfs build would require its own reviewed immutable image/signature chain, exact package closure, measured rootfs identity, and unchanged loader, geometry, import-order and full-suite gates. This probe alone does not prove rootfs package-maintainer scripts or a native build will succeed.

## Publication and testing

Only an independently reviewed source index and exact public allowlist may be published. The generated workflow is intentionally not indexed, avoiding a circular digest. `recipe/verify_workflow_contract.py` renders the complete workflow from the reviewed index hash and checks byte-for-byte publication parity. Tests must pass from a fresh source-index-only materialization with no workflow present, under a clean environment and isolated Python with site hooks/bytecode disabled. Unit fixtures must not execute namespaces, uidmap helpers or a native candidate.

The proposed standalone workflow is `.github/workflows/f2c-capability.yml`, helpers under `deploy/f2c-capability`, restricted to repository `peakpeng666/URP` and branch `fix/agriculture-compatibility-20261022`, push changes to that workflow only or explicit dispatch. It uses the standard `ubuntu-22.04` runner, read-only repository permission, no image publication and no artifact/cache upload. Raw test, authentication and capability evidence remains private and ephemeral on the runner. Unexpected bootstrap/shell stderr is discarded before any path-bearing operation; stage failures remain terminal and are projected only through fixed finite labels. The project's diagnostic output consists only of reviewed finite labels, never raw logs, host paths, usernames, installed versions or exception text. Standard GitHub checkout and job metadata is emitted separately by the platform and is not covered by this project-output guarantee.

Acceptance requires the final verified `stage=capability status=PASS code=OK`; a green workflow conclusion alone is not evidence of capability success.

Scientific source context remains `18557cfc61f291e8ac5fa4a80d9df212e1df0030`. There is no application checkout or scientific test execution in this capability-only workflow.

## Official references

- Exact runner PostgreSQL provisioning: https://github.com/actions/runner-images/blob/90417558da49483fcc9279962bcfb099eba367e8/images/ubuntu/scripts/build/install-postgresql.sh
- Exact container-tool provisioning: https://github.com/actions/runner-images/blob/90417558da49483fcc9279962bcfb099eba367e8/images/ubuntu/scripts/build/install-container-tools.sh
- Versioned Podman rootless requirements: https://docs.podman.io/en/v3.4.4/markdown/podman.1.html#rootless-mode
- Versioned util-linux namespace source: https://github.com/util-linux/util-linux/blob/v2.37.2/sys-utils/unshare.c
- Linux namespace FD ioctl: https://man7.org/linux/man-pages/man2/ns_get_nstype.2const.html
- PGDG archive policy: https://apt-archive.postgresql.org/

## If a prerequisite is absent

- Missing or unauthenticated existing uidmap/unshare/interpreter: stop. Installing an official package or setuid helper is not an automatic fallback in this workflow. First review the exact missing facility and whether a separate authorized provisioning action is appropriate.
- Missing/short subordinate UID or GID grant: stop. Adding an allocation would change the existing access configuration and is outside this probe. A separately reviewed authenticated-provider strategy may avoid that change; do not silently substitute ownership flattening.
- Group-drop, mount, nested-user/network or kernel-FD proof unavailable: stop with the specific finite capability code. Do not change sysctls, AppArmor, seccomp, container privileges or offline guards to turn it into a pass.
- Successful capability proof: prepare a separately reviewed immutable signed Jammy rootfs/input plan. It remains necessary to establish package-script compatibility, authentic file ownership, complete closure, target ABI, exact provider maps and unchanged scientific tests before any candidate is accepted.

- Runner permission provisioning: https://github.com/actions/runner-images/blob/90417558da49483fcc9279962bcfb099eba367e8/images/ubuntu/scripts/build/configure-system.sh#L12-L13

## V3 optimized-Python hardening

V2 was not published: an additional optimized-Python fixture run exposed assertions being removed from two workflow bootstrap bodies. V3 replaces those security-significant assertions with explicit invariant checks, preserving every predicate and bounded failure output. The normal workflow continues to use its fixed isolated interpreter flags. Both normal and optimized source/index-only fixtures are required. This is not evidence of an observed hosted bypass.

The production preparation success code is `CAP_INPUTS_VERIFIED`; final capability success is exactly `stage=capability status=PASS code=OK`. `PROVED` appears only in synthetic projector fixtures and is not accepted by the production public-code contract.
