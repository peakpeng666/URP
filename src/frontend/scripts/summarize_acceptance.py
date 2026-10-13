"""Index final production-browser evidence without treating old diagnostic runs as PASS."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:4173"
REPORTS = {
    "all_views_and_viewports": "product/visual-report.json",
    "overview_science_and_focus": "product-overview/overview-report.json",
    "failures_and_recovery": "product-errors/errors-report.json",
    "samples_and_risk": "product-browse/browse-report.json",
    "replay_interactions": "product-functional.json",
    "touch_and_reduced_motion": "product-mobile/mobile-report.json",
    "source_evidence": "product-evidence/evidence-report.json",
    "canvas_all_bins": "canvas-audit/canvas-audit.json",
    "observed_curve_semantics": "curve-audit.json",
    "browser_zoom_overview": "product-browser-zoom/browser-zoom.json",
    "browser_zoom_replay": "product-replay-browser-zoom/browser-zoom.json",
}


def main() -> int:
    suites = []
    for name, relative in REPORTS.items():
        path = ROOT / "artifacts/codex-browser" / relative
        item = {"name": name, "report": path.relative_to(ROOT).as_posix()}
        try:
            content = path.read_bytes()
            report = json.loads(content)
            valid = report.get("status") == "PASS" and report.get("base", "").startswith(BASE)
            # Filtered checks and development-only results cannot certify a full suite.
            if report.get("filter") or report.get("checkFilter") or report.get("testFilter"):
                valid = False
            if name == "replay_interactions" and not report.get("completeUISuite"):
                valid = False
            item.update(status="PASS" if valid else "FAIL", reported_status=report.get("status"),
                        base=report.get("base"), sha256=hashlib.sha256(content).hexdigest(),
                        checks=len(report.get("checks", report.get("pages", report.get("cases", [])))))
        except (OSError, ValueError) as error:
            item.update(status="MISSING_OR_INVALID", error=str(error))
        suites.append(item)
    result = {
        "schema_version": 1,
        "status": "PASS" if all(x["status"] == "PASS" for x in suites) else "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "scope": "Production build in Chromium; all listed suites must PASS, separately from scientific validation",
        "suites": suites,
        "limitations": ["Emulated phones, not physical devices", "WSL, not native Ubuntu",
                        "Page zoom set by real Chromium tabs API, not manual menu operation",
                        "Earlier diagnostics are preserved as development history, not final acceptance"],
    }
    destination = ROOT / "artifacts/browser_acceptance.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
