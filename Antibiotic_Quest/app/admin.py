"""Admin page: question review, AI drafting, data export and one-click analysis."""
import functools
import hmac
import os
import subprocess
import sys
from datetime import date, datetime

from flask import (Blueprint, Response, abort, current_app, jsonify, render_template, request,
                   send_from_directory)

from . import exports, llm
from .db import DEMO_REVIEWER, ROOT, get_db

bp = Blueprint("admin", __name__)
STATUSES = ("pending_review", "approved", "needs_edit", "rejected")
RUNS_DIR = os.path.join(ROOT, "exports")


def require_token(fn):
    @functools.wraps(fn)
    def wrapper(*a, **k):
        given = request.headers.get("X-Admin-Token") or request.args.get("token") or ""
        if not hmac.compare_digest(given, current_app.config["ADMIN_TOKEN"]):
            return jsonify({"error": "Wrong or missing admin token."}), 401
        return fn(*a, **k)
    return wrapper


@bp.get("/admin")
def admin_page():
    return render_template("admin.html")


@bp.get("/api/admin/stats")
@require_token
def stats():
    db = get_db()
    one = lambda sql, *a: db.execute(sql, a).fetchone()[0]
    q_by_status = dict(db.execute("SELECT review_status, COUNT(*) FROM questions GROUP BY review_status").fetchall())
    llm_by_status = dict(db.execute("SELECT review_status, COUNT(*) FROM questions WHERE drafted_by LIKE 'LLM%' "
                                    "GROUP BY review_status").fetchall())
    approved_by_level = dict(db.execute("SELECT level, COUNT(*) FROM playable_questions GROUP BY level").fetchall())
    runs = [dict(r) for r in db.execute("SELECT * FROM llm_runs ORDER BY run_id DESC LIMIT 10")]
    return jsonify({
        "participants": one("SELECT COUNT(*) FROM participants WHERE is_synthetic=0"),
        "test_runs": one("SELECT COUNT(*) FROM participants WHERE is_synthetic=1"),
        "pre_done": one("SELECT COUNT(DISTINCT t.participant_id) FROM test_responses t JOIN participants p "
                        "ON p.participant_id=t.participant_id WHERE t.phase='pre' AND p.is_synthetic=0"),
        "post_done": one("SELECT COUNT(DISTINCT t.participant_id) FROM test_responses t JOIN participants p "
                         "ON p.participant_id=t.participant_id WHERE t.phase='post' AND p.is_synthetic=0"),
        "answers": one("SELECT COUNT(*) FROM answer_events e JOIN participants p ON p.participant_id=e.participant_id "
                       "WHERE p.is_synthetic=0"),
        "questions": q_by_status, "llm_questions": llm_by_status, "approved_by_level": approved_by_level,
        "demo_approved": one("SELECT COUNT(*) FROM questions WHERE review_status='approved' AND reviewer=?",
                             DEMO_REVIEWER),
        "llm_runs": runs, "gemini_configured": bool(current_app.config.get("GEMINI_API_KEY")),
        "gemini_model": current_app.config.get("GEMINI_MODEL"),
    })


@bp.get("/api/admin/questions")
@require_token
def list_questions():
    db = get_db()
    sql, args = "SELECT * FROM questions WHERE 1=1", []
    if request.args.get("status") in STATUSES:
        sql += " AND review_status=?"
        args.append(request.args["status"])
    if request.args.get("level", "").isdigit():
        sql += " AND level=?"
        args.append(int(request.args["level"]))
    sql += " ORDER BY level, question_id"
    facts = {r["fact_id"]: dict(r) for r in db.execute("SELECT * FROM facts")}
    out = []
    for q in db.execute(sql, args):
        d = dict(q)
        d["facts"] = [facts[f] for f in (q["fact_ids"] or "").split(";") if f in facts]
        out.append(d)
    return jsonify(out)


@bp.post("/api/admin/questions/<qid>/review")
@require_token
def review(qid):
    d = request.get_json(silent=True) or {}
    if d.get("status") not in STATUSES:
        return jsonify({"error": "status must be one of " + ", ".join(STATUSES)}), 400
    if d["status"] != "pending_review" and not str(d.get("reviewer", "")).strip():
        return jsonify({"error": "Enter the reviewer's name first."}), 400
    db = get_db()
    with db:
        cur = db.execute("UPDATE questions SET review_status=?, reviewer=?, review_date=?, review_notes=? "
                         "WHERE question_id=?",
                         (d["status"], str(d.get("reviewer", "")).strip() or None, date.today().isoformat(),
                          str(d.get("notes", "")).strip() or None, qid))
    if cur.rowcount == 0:
        return jsonify({"error": "Unknown question"}), 404
    return jsonify({"ok": True})


@bp.post("/api/admin/drafts")
@require_token
def make_drafts():
    d = request.get_json(silent=True) or {}
    try:
        res = llm.draft_questions(get_db(), int(d.get("level", 1)), d.get("difficulty", "medium"),
                                  int(d.get("n", 3)), current_app.config.get("GEMINI_API_KEY"),
                                  current_app.config.get("GEMINI_MODEL"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(res), (200 if not res["error"] else 502)


@bp.get("/api/admin/export/<name>")
@require_token
def export(name):
    if name not in exports.EXPORTS:
        abort(404)
    fname, fn = exports.EXPORTS[name]
    header, rows = fn(get_db(), request.args.get("include_test") == "1")
    return Response(exports.to_csv_text(header, rows), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={fname}"})


@bp.post("/api/admin/analysis")
@require_token
def run_analysis():
    d = request.get_json(silent=True) or {}
    include_test = bool(d.get("include_test"))
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join(RUNS_DIR, run_id)
    paths = exports.write_all(get_db(), os.path.join(folder, "data"), include_test)
    with open(paths["pre_post"], encoding="utf-8-sig") as f:
        n_rows = sum(1 for _ in f) - 1
    if n_rows < 3:
        return jsonify({"error": f"Only {n_rows} participant(s) in the export. Collect at least 3 complete "
                                 "pre/post tests (or tick 'include test runs').", "run_id": run_id}), 400
    cmd = [sys.executable, os.path.join(ROOT, "analysis", "analysis.py"), "--prepost", paths["pre_post"],
           "--log", paths["answer_log"], "--levels", paths["gameplay"], "--out", os.path.join(folder, "results")]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=300)
    if proc.returncode != 0:
        return jsonify({"error": "Analysis failed", "log": (proc.stdout + proc.stderr)[-3000:], "run_id": run_id}), 500
    res = os.path.join(folder, "results")
    with open(os.path.join(res, "summary.md"), encoding="utf-8") as f:
        summary = f.read()
    charts = sorted(os.listdir(os.path.join(res, "charts")))
    return jsonify({"run_id": run_id, "summary": summary, "charts": charts,
                    "folder": os.path.relpath(folder, ROOT)})


@bp.get("/api/admin/analysis/<run_id>/charts/<path:fname>")
@require_token
def analysis_chart(run_id, fname):
    if not run_id.replace("_", "").isdigit():
        abort(404)
    return send_from_directory(os.path.join(RUNS_DIR, run_id, "results", "charts"), fname)
