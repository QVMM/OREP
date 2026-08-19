#!/usr/bin/env python3
"""Batch re-render PDF reports for completed scoring sessions.

Reads result_*.json under uploads/results, applies jury_enabled from env map
or defaults to false when unknown, strips fake jury_review, regenerates PDF
into uploads/reports/report_{id}.pdf
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Allow `python scripts/rerender...` from container /app
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload-dir", default=os.getenv("UPLOAD_DIR", "/app/uploads"))
    parser.add_argument(
        "--jury-map",
        default="",
        help="JSON object sessionId->bool, e.g. '{\"39\": false, \"38\": true}'",
    )
    parser.add_argument("--only", default="", help="Comma session ids, empty=all result_*.json")
    args = parser.parse_args()

    upload = Path(args.upload_dir)
    results_dir = upload / "results"
    reports_dir = upload / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    jury_map: dict[str, bool] = {}
    if args.jury_map:
        jury_map = {str(k): bool(v) for k, v in json.loads(args.jury_map).items()}

    only = {x.strip() for x in args.only.split(",") if x.strip()}

    from app.services import report_service

    files = sorted(results_dir.glob("result_*.json"))
    ok, fail = 0, 0
    for path in files:
        sid = path.stem.replace("result_", "")
        if only and sid not in only:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("not object")
            data.setdefault("meeting_id", sid)
            if sid in jury_map:
                data["jury_enabled"] = jury_map[sid]
            else:
                data["jury_enabled"] = bool(data.get("jury_enabled") or data.get("juryEnabled"))
            # 若磁盘上有已完成评审团会话，默认视为启用（避免 web 有分、PDF 漏章）
            if sid not in jury_map and not data["jury_enabled"]:
                try:
                    from app.services.jury.scoring_service import get_latest_jury_session
                    sess = get_latest_jury_session(sid)
                    if isinstance(sess, dict) and (
                        sess.get("status") == "completed"
                        or sess.get("judge_reports")
                        or (sess.get("aggregate") or {}).get("trimmed_average_score") is not None
                    ):
                        data["jury_enabled"] = True
                except Exception:
                    pass
            # Strip fake judges when disabled
            if not data["jury_enabled"]:
                ai = data.get("ai_score")
                if isinstance(ai, dict):
                    ai.pop("jury_review", None)
            out = report_service.generate_report(data, str(reports_dir))
            print(f"OK {sid} -> {out}")
            ok += 1
        except Exception as exc:
            print(f"FAIL {sid}: {exc}")
            fail += 1
    print(f"done ok={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
