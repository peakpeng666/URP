# Public package boundary

Only paths explicitly listed in public_allowlist.json belong in the downloadable or hosted package. No recursive copy of the parent workspace is authorized by this manifest.

Included: cleaned results, primary and clearly separate post-hoc metrics, exact synthetic inputs, raw scientific HTTP requests/responses/model content, process measurements, official template/license text, minimal offline checker/scoring source, and route visuals/data.

Excluded: model weights, executable runtime packages/binaries/shared libraries, installed dependencies, caches, internal coordination/conversation material, private review notes and working notes. Verification facts are summarized without shipping private reviews. Raw body/content/request copies are byte-identical; parsed HTTPheaders/status retain their proper qualification.

Offline validation: python scientific_source/verify_saved.py

This package does not launch the model or include any credential. Actual model execution would require the separately downloaded official fixed assets and a separately specified run protocol.
