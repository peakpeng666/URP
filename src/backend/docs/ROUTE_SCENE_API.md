# Route-scene v1 contract for GrokBot and the robotics visualization bridge

Status: read-only backend prototype. Frontend implementation remains GrokBot's responsibility. This change adds no solver/recommender execution, no web write-task endpoint, no ROS installation, and no robot navigation interface.

## Endpoint

`GET /api/v1/experiments/{experiment_id}/runs/{run_id}/route-scene?revision=1`

- Select a run through the existing `/api/experiments/{experiment_id}/runs` API. The scene endpoint does not select or rank a run.
- Omit `revision` to resolve the latest imported revision once; every response includes the resolved revision, experiment fingerprint, and revision-pinned evidence URLs. Save and reuse those identities for a reproducible view.
- Only one positive-integer `revision` parameter is accepted. Unknown parameters, duplicate revision parameters, blank revisions, coordinate/unit overrides, and physical-readiness overrides are rejected.
- Successful response: HTTP 200, `application/json; charset=utf-8`.
- POST with a valid query: HTTP 405 (`read_only_routes`), before request-body parsing. A malformed revision can return HTTP 400 first because revision parsing precedes method rejection. Neither path mutates data. Other HTTP methods are unsupported by the server and cannot mutate the scene.
- Invalid revision/ID/query: HTTP 400. Missing experiment, run, revision, or structured routes: HTTP 404. Invalid/nonfinite/inconsistent scene geometry: HTTP 409 (`invalid_route_scene`). Existing error envelope remains `{ "error": "code", "message": "..." }`.
- This API is hosted by the existing loopback-only server. No CORS, remote hosting, access-control or frontend deployment changes are included.

Machine-readable contract: [`route_scene_v1.schema.json`](route_scene_v1.schema.json), JSON Schema Draft 2020-12. Canonical example: [`../tests/fixtures/route_scene_v1.json`](../tests/fixtures/route_scene_v1.json). The example is generated from explicitly synthetic contract-test data, not research results.

## Exact top-level fields

All fields below are always present. JSON `null` means missing/not applicable, never zero. The server serializes strict JSON with `allow_nan=False`; consumers must reject NaN and Infinity while parsing. The schema's `x-json-policy.allow_nonfinite=false` records this parser requirement, not an additional standard JSON Schema keyword.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | integer, exactly 1 | Version of this scene contract, separate from existing route APIs. |
| `scene_type` | string, `route_scene` | Scene document discriminator. |
| `experiment_id`, `run_id`, `instance_id` | strings | Original imported identities. |
| `revision` | positive integer | Resolved immutable experiment revision. |
| `experiment_fingerprint` | SHA-256 hex string | Existing store's descriptor-plus-artifacts fingerprint; not a newly invented research identity. |
| `geometry_kind` | string, `visit_order_polyline` | Straight connections between visits, not computed drivable geometry. |
| `simulation_ready` | boolean, always false in v1 | Current adapters contain no independently supplied physical map context. |
| `frame` | object | Defined below. |
| `units` | object | Defined below. |
| `semantics` | object | Source route semantics unchanged, including objective/load/time-window caveats when supplied. |
| `depot` | node object | Node 0 from the source. |
| `task_nodes` | array of node objects | All input nodes other than depot, in source order, including unserved nodes. |
| `vehicles` | array of vehicle objects | Available normalized geometry only; empty if no candidate. |
| `metrics` | object | Known checker/source metrics, defined below. |
| `status` | object | Source and solution states are kept separate. |
| `unserved_task_ids` | integer array or null | Missing-task IDs supplied by the normalized source run; null if no candidate, not a fabricated all-missing list. For invalid candidates this is not validated coverage. |
| `recommendation` | object | Explicit absence of linked recommendation evidence. |
| `provenance` | object | Original source identity and revision-pinned evidence URLs. |
| `limitations` | string array | Required interpretation caveats. Do not strip them when exporting a scene elsewhere. |

### Frame and units

`frame` has exactly:

- `id`: `benchmark_xy`. A diagram coordinate identifier, not a shared physical frame across experiments, and not automatically ROS `map`, `odom` or `base_link`.
- `coordinate_system`: unchanged source string or null. Current supported archives use `synthetic_cartesian` or `archived_benchmark_cartesian`.
- `axis_order`: `["x", "y"]`.
- `is_geographic`, `is_road_network`: unchanged source booleans or null; current archives are false for both.
- `physical_frame_id`: null.
- `meters_per_coordinate_unit`: null.

`units` has exactly:

- `coordinate`, `distance`: source `semantics.distance_unit`, or null. Current archives declare `arbitrary_distance_units`; do not relabel these as meters or longitude/latitude.
- `schedule_time`: source `semantics.time_unit`, or null. Current archives declare `arbitrary_time_units`; these are not physical motion seconds.
- `compute_time`: `seconds` only when at least one explicit non-null `cpu_seconds` or supported `*_s` source timing field exists; otherwise null. This describes recorded computational timing, not schedule time, and does not convert an algorithm budget from milliseconds.
- `demand`: null. No physical demand unit is declared by these source adapters.

Frontend screen scaling is a display transform only. A ROS bridge may create a clearly marked nonmetric diagram frame, but cannot derive a physical scale, TF transform, collision-free path, odometry or navigation goal from this document. An independently evidenced map registration, metric conversion, robot geometry, kinematics and collision checks would require a separate validated physical-context contract. V1 does not accept them as query overrides and stays `simulation_ready=false`.

### Nodes

Each node object has exactly:

- `node_id`: original integer ID, depot is 0.
- `x`, `y`: finite original coordinate numbers, without scaling or rounding.
- `demand`: recorded demand number or null.
- `service_duration`: recorded service duration or null, in `units.schedule_time`.
- `time_window`: two-number `[open, close]` array or null, in `units.schedule_time`. Current semantics are inclusive start-of-service bounds, not arrival bounds.

### Vehicles

Each vehicle object has exactly:

- `vehicle_id`: original integer identity. IDs can be sparse, e.g. vehicle 2 can be the only exported vehicle. Do not enumerate the array and replace its ID.
- `visit_node_ids`: original path order including depot departure/return, e.g. `[0,1,2,0]`. Repeated visits stay repeated. An actual empty-vehicle path `[0,0]` may exist; no candidate is instead `vehicles=[]`.
- `polyline`: parallel array of original `[x,y]` coordinates, one per `visit_node_ids` entry. Segments simply join visit points. No orientation, obstacle clearance, dynamics, timestamped trajectory or motion command is synthesized.
- `metrics`: exactly `distance`, `return_time`, `cumulative_served_demand`, each number or null. They are copied from normalized vehicle `distance`, `return_time`, and `load`; cumulative served demand is not physical onboard load.
- `stops`: the existing normalized checker schedule objects unchanged. Depending on source format they include `node`, `sequence`, `arrival`, `wait`, `start`, `service_start`, `depart`, `window_open`, `window_close`, `lateness`, `demand`, `leg_distance`, `load_before`, `load_after`, `onboard_load`. Do not assume these optional source fields are universally present. `onboard_load` remains null. These are checker calculations, not observed robot telemetry.

Structurally invalid source routes without normalized geometry may be absent. An invalid run may therefore have a candidate but no renderable vehicle geometry. Keep its invalid state visible and use the pinned original run/evidence for full diagnostics; never present the available subset as a complete validated route.

For invalid candidates, `unserved_task_ids` preserves normalized source data, not a verified service-completion claim. Some adapters derive these IDs from raw route visits even when the checker rejects that route's structure; the list can therefore disagree with `served_task_count`. Do not infer that an omitted task was successfully served or reconstruct a verified coverage count from this list. This export does not rewrite the existing run API's evidence.

### Metrics

`metrics` has exactly:

- `total_distance`: `run.checker.audit.total_distance`, or null without an audit. It can exist for partial/invalid candidates and is not automatically a success score.
- `full_service_distance`: the same checker distance only when the original run has `full_service_success=true`; otherwise null.
- `served_task_count`: `run.checker.audit.served_unique`, or null without an audit.
- `task_count`: number of input nodes excluding depot, derived without running a solver.
- `recorded`: only available source keys from the allowlist below. Missing source keys remain absent; explicit source nulls remain null. Numeric values are not reinterpreted, optimized or re-ranked.

Allowed `recorded` keys:

`cpu_seconds`, `solve_wall_s`, `solve_cpu_s`, `model_wall_s`, `model_cpu_s`, `total_wall_s`, `total_cpu_s`, `full_oracle_objective`, `full_gap_percent`, `same_served_mask_optimum`, `same_served_mask_gap_percent`, `coverage_shortfall`, `full_gap_original_percent`, `objective_integer`, `vehicles_used`, `original_distance`, `full_service_distance`, `bks_gap_percent`.

Every present allowlisted value must be a finite number or null. Boolean, string, array, and object values are rejected with `409 invalid_route_scene`, not coerced. This export check does not change legacy import or run APIs.

Timing scope stays in the field name: solve time is not total time, CPU time is not wall time. `objective_integer` is the archived integer-encoded objective, not unscaled physical distance. Recorded oracle/gap fields retain their original evidence and interpretation; exporting them provides no new optimality proof. The original run API remains the source of algorithm, budget, solver/checker diagnostics and fields not included in the scene allowlist.

### Status and recommendation

`status` has exactly `execution_status`, `source_status`, `solution_status`, `full_service_success`, and `has_candidate`.

- First four are copied unchanged from the normalized run. `solution_status` is one of `feasible`, `partial`, `invalid`, `infeasible`, `no_solution`, `unknown`.
- `has_candidate` means source `run.routes` is not null; it does not mean feasible or fully renderable.
- Execution completed is not route feasible. Partial is not full success. A solver timeout/no solution is not a proof of problem infeasibility.

`recommendation` has exactly:

- `status`: always `not_available` in v1.
- `selected_run_id`: null.
- `evidence`: null.
- `reason`: explanatory string.

The user-selected run is already identified by root `run_id`. It is not a recommendation. A cheapest returned feasible result from descriptive comparison is also not a learned recommendation, optimality certificate or algorithm-selection-model prediction. A future recommendation display requires separately linked evidence for that specific input/run and a separately versioned supported contract.

### Provenance

`provenance` has exactly:

- `run`: original run provenance object unchanged, including original/derived identity labels, source artifact ID/locator, run-line hash, problem/research protocol hashes and input identity where recorded.
- `input`: original `input_provenance` object unchanged; the archival public-input official byte-identity caveat is preserved.
- `index_artifact`: exactly `id`, `sha256`, `url`. The hash is the existing stored route-index artifact digest; URL is relative to the current backend and pinned with `?revision=N`.
- `source_run_url`: existing run-detail API URL relative to the current backend, pinned to the same revision.

Do not reinterpret the run hash as a hash of the scene JSON or replace source hashes with new serialization hashes. `RouteReader` checks stored artifact integrity through the existing store; exporting creates no new database revision and does not read mutable external source paths.

## Suggested frontend behavior, not frontend implementation

1. Fetch a chosen run's scene and retain resolved revision/fingerprint.
2. Render depot, all task nodes, and one distinctly styled line per native vehicle ID. Use visit order and existing stop sequence for labels.
3. Display `solution_status`, full-service success, units, and `geometry_kind` visibly. Distinguish unserved nodes from missing candidate evidence.
4. Show only applicable metrics and label missing values as unknown/not applicable, not zero. Do not rank partial/invalid candidates alongside full-service costs.
5. Show “Recommendation unavailable” until an explicit supported recommendation evidence contract exists.
6. Display the nonphysical-route warning. Offer the revision-pinned provenance link for audit. Do not label these polylines as collision-free or navigation-ready.

## Verification and reproduction

From `src/backend`:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
ROUTE_SCENE_INTEGRATION_REPORT=/tmp/route_scene_integration.json \
  python3 -m unittest discover -s tests -p integration_route_scene.py
```

The first suite is standard-library-only. The explicit integration test also uses the test environment's `jsonschema` package for Draft 2020-12 validation; this is not a new backend runtime dependency.

The integration imports fresh synthetic fixtures for legacy frozen, mature solver, archived public, and solver-portfolio formats. It makes actual loopback HTTP requests, validates all 14 scenes, cross-checks the old run API, verifies artifact SHA-256, exercises POST rejection, and checks source-file and database bytes remain unchanged during export. Public fixture protocol/parameter hash pins are patched only within test scope; production pins and benchmark solvers are unchanged.

This verifies adapter behavior on synthetic contract fixtures, not a new benchmark, physical simulation, ROS runtime, robot motion, frontend visual QA, deployment, or revalidation of unavailable historical research archives.
