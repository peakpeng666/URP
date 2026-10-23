# Future native Jammy package preparation

This is an implemented preparation path, not evidence that a runner has been launched or a native build has passed.

CLI, on an explicitly authorized Ubuntu 22.04 amd64 runner:

- `/usr/bin/python3 recipe/prepare_jammy_packages.py --root /absolute/fresh/candidate` resolves, downloads and verifies. It does not install. Its output has `installed: false` and cannot satisfy the build guard.
- Add `--install` only for the authorized disposable runner preparation. The script then installs the exact verified transaction and verifies the complete before/after package inventory. It does not publish files, launch workflows or invoke Codex.

Requirements: system Python with Ubuntu's `python3-apt` (native APT 2.4 ABI), `apt-get`, `gpgv`, `dpkg-deb`, a pre-existing trusted Ubuntu archive keyring, and noninteractive sudo only when installation is selected. Missing prerequisites are reported; the script does not bootstrap them from an unknown source. Use `/usr/bin/python3`, not the project's separate Python 3.12 interpreter, for this script.

## Flow

1. Fail on Debian, another Ubuntu release or non-amd64 architecture before creating preparation state.
2. Capture base dpkg status and complete installed inventory. Fetch missing official snapshot metadata into candidate-local storage. InRelease hashes and sizes are pinned in reviewed source. Verify each signature with the runner's trusted keyring before fetching or reading its package indexes; check every index against authenticated SHA256 and size.
3. Build a candidate-local, signed, read-only APT repository from that metadata. All APT configuration, package lists, logs and download caches are candidate-local. No host sources or pinning files are edited and no external repository participates.
4. Use native `apt_pkg` to solve the exact root requests. Walk its actually satisfied Depends/Pre-Depends targets for requested roots, all changed packages and installed Essential packages. Include all already-installed satisfying alternatives conservatively. This is the full relevant package closure, not merely the install delta.
5. An older relevant installed version missing from the fixed snapshot may only be upgraded to an authenticated version and re-solved. Missing provenance, a newer installed version needing downgrade, changed package holds, any removal/downgrade, or an unsatisfied constraint stops preparation. No unrelated blanket system upgrade or autoremove occurs.
6. Download every closure archive from the fixed official snapshot, including already-installed dependencies. Check signed SHA256/size and archive control identity before any installation. Ask APT only for cache naming, stage the independently verified payloads, then re-simulate and compare the exact transaction.
7. Installation uses `--no-remove --no-download`; no downgrade permission is supplied. Recheck dpkg status before installation, verify the complete post-install inventory equals the expected transaction, run APT's consistency check, and compare the pkg-config executable/alias to its authenticated package bytes.
8. Only successful installation produces `installed: true` and `installation_verified: true`. `package-preparation.json` includes candidate-local SHA256 file rows, signed metadata, full closure archives, base/post inventories, solver transaction, logs and provider decisions. The host preparer independently checks this receipt and measures the actual host inputs afterward.

Failure leaves evidence and no successful readiness receipt. Choose a new fresh preparation root after correcting a blocker; the script does not blindly resume or overwrite a partial transaction.

## pkgconf versus pkg-config

The official GitHub Ubuntu2204 inventory read on 2026-10-22 identifies image 20261012.322.1 and lists `pkg-config 0.29.2-1ubuntu3`; it does not establish that every runner has pkgconf. Actual dpkg state is authoritative.

Signed Jammy metadata identifies `pkgconf 1.8.0-1` as providing `pkg-config (= 0.29-1)` and breaking `pkg-config (>= 0.29-1)`. If that authenticated pkgconf provider is already installed alone, the preparer keeps its exact version, records the explicit supported root-provider alias, requires APT to satisfy all actual dependency constraints, and verifies installed executable bytes against its archive. It does not attempt to co-install pkg-config or remove pkgconf. Both providers, an unknown provider/version, wrong executable ownership, incompatible dependencies or any removal proposal cause a clear stop.

Official references:
- https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2204-Readme.md
- https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2204-Readme.md
- https://snapshot.ubuntu.com/
- https://apt-team.pages.debian.net/python-apt/library/apt_pkg.html

## Verification completed here

The stdlib fixture suite covers OS guards, signed metadata parsing, archive path restrictions, bad hashes/oversized downloads, native APT API fixtures, dependency alternatives/cycles, provider conflicts/bytes, exact transaction parsing, holds/removals/downgrades, stale inventory and unexpected post-install changes. The actual Debian-host invocation exits 2 before preparation state exists. This is not a native Jammy execution test. No APT update, package installation or experiment was run here.
