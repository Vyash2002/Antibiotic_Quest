"""Player-facing JSON API."""
import json
import os
import random
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from .content import (BOARD_CELLS, LEVEL5_OWN, LEVELS, QUESTIONS_PER_LEVEL, instrument, knowledge_key,
                      public_instrument)
from .db import get_db

bp = Blueprint("api", __name__, url_prefix="/api")

POINTS_CORRECT, POINTS_WITH_HINT = 10, 7
LANGS = ("en", "hi")


def now():
    return datetime.now().isoformat(timespec="seconds")


def bad(msg, code=400):
    return jsonify({"error": msg}), code


def body():
    return request.get_json(silent=True) or {}


def _session(db, session_id, participant_id=None):
    row = db.execute("SELECT * FROM game_sessions WHERE session_id = ?", (session_id,)).fetchone()
    if row is None or (participant_id and row["participant_id"] != participant_id):
        return None
    return row


def _question_payload(q):
    n = 2 if q["question_type"] == "tf" else 4
    letters = "ABCD"[:n]
    return {
        "id": q["question_id"], "type": q["question_type"], "difficulty": q["difficulty"],
        "options": list(letters),
        "en": {"question": q["question_en"], "options": [q[f"option_{l.lower()}_en"] for l in letters],
               "hint": q["hint_en"]},
        "hi": {"question": q["question_hi"] or q["question_en"],
               "options": [q[f"option_{l.lower()}_hi"] or q[f"option_{l.lower()}_en"] for l in letters],
               "hint": q["hint_hi"] or q["hint_en"]},
    }


# ------------------------------------------------------------------ config
@bp.get("/config")
def config():
    db = get_db()
    counts = dict(db.execute("SELECT level, COUNT(*) FROM playable_questions GROUP BY level").fetchall())
    manifest_path = os.path.join(current_app.static_folder, "audio", "manifest.json")
    audio = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            audio = json.load(f)
    levels = [{"level": L, "name": m["name"], "learn": m["learn"], "n_questions": QUESTIONS_PER_LEVEL[L],
               "approved": counts.get(L, 0)} for L, m in LEVELS.items()]
    return jsonify({"levels": levels, "board_cells": BOARD_CELLS, "instrument": public_instrument(),
                    "audio_files": audio, "points": {"correct": POINTS_CORRECT, "with_hint": POINTS_WITH_HINT}})


# ------------------------------------------------------------------ participants
@bp.post("/participants")
def create_participant():
    d = body()
    if d.get("consent") is not True:
        return bad("Consent is required to take part.")
    lang = d.get("language", "en")
    if lang not in LANGS:
        return bad("language must be 'en' or 'hi'")
    demo = d.get("demographics") or {}
    test_run = bool(d.get("test_run"))
    db = get_db()
    prefix = "T" if test_run else "P"
    with db:
        n = db.execute("SELECT COUNT(*) FROM participants WHERE participant_id LIKE ?", (prefix + "%",)).fetchone()[0]
        pid = f"{prefix}{n + 1:03d}"
        while db.execute("SELECT 1 FROM participants WHERE participant_id=?", (pid,)).fetchone():
            n += 1
            pid = f"{prefix}{n + 1:03d}"
        ts = now()
        db.execute("INSERT INTO participants VALUES (?,?,?,?,?,?,?,?,?)",
                   (pid, 1, ts, demo.get("D01") or None, demo.get("D02") or None, demo.get("D03") or None,
                    demo.get("D04") or None, lang, 1 if test_run else 0))
        sid = "S" + uuid.uuid4().hex[:10]
        db.execute("INSERT INTO game_sessions VALUES (?,?,?,?,?,?)",
                   (sid, pid, ts, None, lang, 1 if d.get("audio") else 0))
    return jsonify({"participant_id": pid, "session_id": sid, "test_run": test_run})


# ------------------------------------------------------------------ pre / post test
def _knowledge_score(db, pid, phase):
    key = knowledge_key()
    rows = db.execute("SELECT item_id, response FROM test_responses WHERE participant_id=? AND phase=?",
                      (pid, phase)).fetchall()
    got = {r["item_id"]: r["response"] for r in rows}
    if not all(k in got for k in key):
        return None
    return sum(1 for k, v in key.items() if (got.get(k) or "").strip().lower() == v.lower())


@bp.post("/tests/<phase>")
def save_test(phase):
    if phase not in ("pre", "post"):
        return bad("phase must be 'pre' or 'post'", 404)
    d = body()
    pid = d.get("participant_id", "")
    resp = d.get("responses") or {}
    db = get_db()
    if not db.execute("SELECT 1 FROM participants WHERE participant_id=?", (pid,)).fetchone():
        return bad("Unknown participant", 404)
    inst = instrument()
    allowed = {}
    for sec in ("knowledge", "attitude") + (("feedback",) if phase == "post" else ()):
        for it in inst[sec]:
            allowed[it["id"]] = it
    missing = [i for i, it in allowed.items() if it["required"] and not str(resp.get(i, "")).strip()]
    if missing:
        return bad("Please answer every question before continuing. Missing: " + ", ".join(missing))
    ts = now()
    rows = []
    for item_id, value in resp.items():
        it = allowed.get(item_id)
        if it is None:
            continue
        value = str(value).strip()[:1000]
        if not it["free_text"] and value and value not in [o["value"] for o in it["options"]]:
            return bad(f"Invalid answer for {item_id}")
        rows.append((pid, phase, item_id, value, ts))
    with db:
        db.executemany("INSERT OR REPLACE INTO test_responses VALUES (?,?,?,?,?)", rows)
    out = {"saved": len(rows), "max": len(knowledge_key())}
    if phase == "post":
        out["pre_score"] = _knowledge_score(db, pid, "pre")
        out["post_score"] = _knowledge_score(db, pid, "post")
    return jsonify(out)


# ------------------------------------------------------------------ levels
def _pick_questions(db, level, session_id):
    n = QUESTIONS_PER_LEVEL[level]
    rng = random.Random()
    if level < 5:
        pool = [dict(r) for r in db.execute("SELECT * FROM playable_questions WHERE level=?", (level,))]
        if len(pool) < n:
            return None, len(pool)
        by_diff = {d: [q for q in pool if q["difficulty"] == d] for d in ("easy", "medium", "hard")}
        for v in by_diff.values():
            rng.shuffle(v)
        picked, cycle = [], ["easy", "medium", "hard", "medium", "easy", "hard"]
        i = 0
        while len(picked) < n:
            d = cycle[i % len(cycle)]
            if by_diff[d]:
                picked.append(by_diff[d].pop())
            elif not any(by_diff.values()):
                break
            i += 1
    else:
        own = [dict(r) for r in db.execute("SELECT * FROM playable_questions WHERE level=5")]
        rng.shuffle(own)
        picked = own[:LEVEL5_OWN]
        seen = {r[0] for r in db.execute("SELECT question_id FROM answer_events WHERE session_id=?", (session_id,))}
        others = [dict(r) for r in db.execute("SELECT * FROM playable_questions WHERE level<5")]
        fresh = [q for q in others if q["question_id"] not in seen]
        rng.shuffle(fresh)
        stale = [q for q in others if q["question_id"] in seen]
        rng.shuffle(stale)
        picked += (fresh + stale)[: n - len(picked)]
        if len(picked) < n:
            return None, len(picked)
    order = {"easy": 0, "medium": 1, "hard": 2}
    picked.sort(key=lambda q: order[q["difficulty"]])
    return picked, len(picked)


@bp.post("/levels/<int:level>/start")
def start_level(level):
    if level not in LEVELS:
        return bad("Unknown level", 404)
    d = body()
    db = get_db()
    s = _session(db, d.get("session_id", ""), d.get("participant_id"))
    if s is None:
        return bad("Unknown session", 404)
    existing = db.execute("SELECT question_ids FROM level_progress WHERE session_id=? AND level=?",
                          (s["session_id"], level)).fetchone()
    if existing and existing["question_ids"]:
        ids = existing["question_ids"].split(";")
        qs = [dict(db.execute("SELECT * FROM questions WHERE question_id=?", (i,)).fetchone()) for i in ids]
    else:
        qs, have = _pick_questions(db, level, s["session_id"])
        if qs is None:
            return bad(f"Level {level} needs {QUESTIONS_PER_LEVEL[level]} approved questions but only {have} "
                       "are approved. Approve questions in the admin page, or run "
                       "'python db/init_db.py --approve-all-demo' for a local test.", 409)
        with db:
            db.execute("INSERT OR REPLACE INTO level_progress (session_id, level, started_at, ended_at, "
                       "level_completed, question_ids) VALUES (?,?,?,?,?,?)",
                       (s["session_id"], level, now(), None, 0, ";".join(q["question_id"] for q in qs)))
    answered = {r["question_id"]: dict(r) for r in db.execute(
        "SELECT question_id, selected_option, is_correct, points_awarded FROM answer_events "
        "WHERE session_id=? AND level=?", (s["session_id"], level))}
    return jsonify({"level": level, "board_cells": BOARD_CELLS,
                    "questions": [_question_payload(q) for q in qs], "answered": answered})


@bp.post("/answer")
def answer():
    d = body()
    db = get_db()
    s = _session(db, d.get("session_id", ""), d.get("participant_id"))
    if s is None:
        return bad("Unknown session", 404)
    level, qid = int(d.get("level", 0)), d.get("question_id", "")
    lp = db.execute("SELECT question_ids FROM level_progress WHERE session_id=? AND level=?",
                    (s["session_id"], level)).fetchone()
    if lp is None or qid not in lp["question_ids"].split(";"):
        return bad("This question was not served in this level.")
    q = db.execute("SELECT * FROM questions WHERE question_id=?", (qid,)).fetchone()
    sel = str(d.get("selected_option", "")).upper()
    valid = "AB" if q["question_type"] == "tf" else "ABCD"
    if sel not in valid:
        return bad("selected_option must be one of " + ", ".join(valid))
    prev = db.execute("SELECT * FROM answer_events WHERE session_id=? AND question_id=? AND level=?",
                      (s["session_id"], qid, level)).fetchone()
    if prev:   # already answered (e.g. page refresh): return the stored result, don't double count
        ok, pts, sel = bool(prev["is_correct"]), prev["points_awarded"], prev["selected_option"]
    else:
        ok = sel == q["correct_answer"]
        hint = 1 if d.get("hint_used") else 0
        pts = (POINTS_WITH_HINT if hint else POINTS_CORRECT) if ok else 0
        lang = d.get("language") if d.get("language") in LANGS else s["language"]
        rt = d.get("response_time_ms")
        rt = int(rt) if isinstance(rt, (int, float)) and rt >= 0 else None
        with db:
            db.execute("INSERT INTO answer_events (session_id, participant_id, level, question_id, language, "
                       "attempt_no, selected_option, correct_option, is_correct, hint_used, audio_played, "
                       "response_time_ms, points_awarded, timestamp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (s["session_id"], s["participant_id"], level, qid, lang, 1, sel, q["correct_answer"],
                        int(ok), hint, 1 if d.get("audio_played") else 0, rt, pts, now()))
    return jsonify({"is_correct": ok, "selected_option": sel, "correct_option": q["correct_answer"],
                    "points": pts,
                    "explanation": {"en": q["explanation_en"], "hi": q["explanation_hi"] or q["explanation_en"]}})


@bp.post("/levels/<int:level>/end")
def end_level(level):
    d = body()
    db = get_db()
    s = _session(db, d.get("session_id", ""), d.get("participant_id"))
    if s is None:
        return bad("Unknown session", 404)
    with db:
        db.execute("UPDATE level_progress SET ended_at=?, level_completed=? WHERE session_id=? AND level=?",
                   (now(), 1 if d.get("completed") else 0, s["session_id"], level))
    return jsonify({"ok": True})


@bp.post("/sessions/end")
def end_session():
    d = body()
    db = get_db()
    s = _session(db, d.get("session_id", ""), d.get("participant_id"))
    if s is None:
        return bad("Unknown session", 404)
    with db:
        db.execute("UPDATE game_sessions SET ended_at=? WHERE session_id=?", (now(), s["session_id"]))
    return jsonify({"ok": True})


@bp.get("/results/<pid>")
def results(pid):
    db = get_db()
    if not db.execute("SELECT 1 FROM participants WHERE participant_id=?", (pid,)).fetchone():
        return bad("Unknown participant", 404)
    g = db.execute("SELECT COUNT(*) n, COALESCE(SUM(is_correct),0) c, COALESCE(SUM(points_awarded),0) p "
                   "FROM answer_events WHERE participant_id=?", (pid,)).fetchone()
    return jsonify({"pre_score": _knowledge_score(db, pid, "pre"), "post_score": _knowledge_score(db, pid, "post"),
                    "max": len(knowledge_key()), "game": {"answered": g["n"], "correct": g["c"], "points": g["p"]}})
