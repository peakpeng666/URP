# Real simulation acceptance harness

Execution source is fixed to 18557cfc61f291e8ac5fa4a80d9df212e1df0030. The harness package is checked out at a separate fixed commit supplied by the wrapper; both identities appear independently in the allowlisted summary. A fresh clean source checkout is mandatory, not the dirty local audit checkout.

Interface:

    python acceptance.py --source SOURCE --private-dir NEW_PRIVATE_DIRECTORY --summary SUMMARY --harness-sha FORTY_HEX_COMMIT --stage maze
    python public_summary.py --input SUMMARY --runner-status RUNNER_STATUS

The wrapper owns installation and Xvfb. The harness owns a fresh runtime and gateway, and invokes the unmodified source full_loop.py via its real HTTP API: maze-inspection, recommended algorithm only, ground_truth, follow_path, no GUI or RViz. Full-loop overall wall budget is 1800 seconds. The physical controller's separate budget is reported only if present in its real record, otherwise null. No historical timing is claimed for this new maze run.

PASS requires full-loop PASS, terminal simulation succeeded, at least two finite ground-truth samples with real movement, all positive-count tasks reached, planned and measured actual collision-free map checks, verified solver source and worker interpreter identities, verified source-fixed bridge plus TF/GUI compatibility, complete assets, normal recorded session cleanup, gateway exit 0, full-loop exit 0 and no remaining owned processes. Timeout, forced harness cleanup, missing evidence, wrapper error or wrapper process residue fail closed. The harness never disables original source/ABI/map gates. A random inherited ownership marker and PID start-time check limit cleanup to its own process tree; the outer wrapper independently adopts/checks descendants.

The only public path is public_summary.py, which rebuilds fixed keys and enums, finite bounded numbers, booleans and hex digests. Arbitrary strings, original errors, URLs, absolute paths, API responses and unknown keys are discarded. Absent measurements remain null with not_measured availability. TF/clock live diagnostics are not presently sampled and are not claimed as zero. Raw API outputs, runtime, logs and reports stay beneath the runner temporary directory, never uploaded or cached. The wrapper's final cleanup result can overturn an earlier PASS.

Warehouse is explicitly NOT_RUN. Passing --stage warehouse fails before gateway startup until a reviewed frozen-JSON replay adapter is supplied. It must reuse the recovered five-task geometry and exact spawn, not solve a replacement route. Reconstructed 650-second budget and original missing timing must be disclosed in that subsequent adapter.

Local tests exercise projection, every success gate, missing measurements, corrupt/nonfinite inputs, source mismatch, wrapper cleanup override and a real tagged child cleanup. They are harness tests, not ROS/Gazebo acceptance. No simulator or installer was run during development.

## Startup timing policy

The pinned application uses an Undock-only 35-second simulation budget, a 700-second monotonic wall watchdog, and 30-second clock-progress and required-stream guards. Readiness polling is capped at 1200 wall seconds and remains bounded by the existing overall polling deadline. Cancellation and cleanup have their own bounded wall waits. Nav2 execution budgets, route geometry, collision checks and success criteria are unchanged. The observer records an observed interval, not exact action acceptance/result times.
