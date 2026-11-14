"""End-to-end tests: API flow, exports, analysis run, admin review and AI drafting (mocked).

    pip install pytest
    python -m pytest -q
"""
import json
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402
from app import llm  # noqa: E402
from app.content import instrument  # noqa: E402
from app.db import connect, load_questions  # noqa: E402

TOKEN = "test-token"


@pytest.fixture()
def app(tmp_path):
    dbp = str(tmp_path / "t.db")
    app = create_app({"DATABASE": dbp, "ADMIN_TOKEN": TOKEN, "GEMINI_API_KEY": "fake", "TESTING": True})
    con = connect(dbp)
    load_questions(con, approve_all=True)
    con.close()
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def answers(rng, skill):
    inst = instrument()
    out = {}
    for it in inst["knowledge"]:
        vals = [o["value"] for o in it["options"]]
        out[it["id"]] = it["key"] if rng.random() < skill else rng.choice([v for v in vals if v != it["key"]])
    for it in inst["attitude"]:
        out[it["id"]] = str(rng.randint(1, 5))
    return out


def play_one(client, rng, test_run=False, finish=True):
    p = client.post("/api/participants", json={"consent": True, "language": rng.choice(["en", "hi"]),
                                               "demographics": {"D01": "22-25"}, "test_run": test_run}).get_json()
    pid, sid = p["participant_id"], p["session_id"]
    assert client.post("/api/tests/pre", json={"participant_id": pid, "responses": answers(rng, 0.45)}).status_code == 200
    for level in range(1, 6):
        r = client.post(f"/api/levels/{level}/start", json={"session_id": sid, "participant_id": pid})
        assert r.status_code == 200, r.get_json()
        qs = r.get_json()["questions"]
        assert len(qs) == (8 if level == 5 else 5)
        for q in qs:                                                   # answers never sent to the browser
            assert not {"correct", "correct_answer", "explanation"} & (set(q) | set(q["en"]) | set(q["hi"]))
        for q in qs:
            res = client.post("/api/answer", json={
                "session_id": sid, "participant_id": pid, "level": level, "question_id": q["id"],
                "selected_option": rng.choice(q["options"]), "hint_used": rng.random() < 0.2,
                "response_time_ms": rng.randint(3000, 20000), "language": "en"}).get_json()
            assert set(res) >= {"is_correct", "correct_option", "explanation", "points"}
        client.post(f"/api/levels/{level}/end", json={"session_id": sid, "participant_id": pid,
                                                      "completed": finish or level < 3})
        if not finish and level == 3:
            break
    post = answers(rng, 0.7)
    post.update({"FB01": "4", "FB02": "5", "FB03": "3", "FB04": "4", "FB05": "More levels"})
    r = client.post("/api/tests/post", json={"participant_id": pid, "responses": post}).get_json()
    assert r["post_score"] is not None and r["pre_score"] is not None
    client.post("/api/sessions/end", json={"session_id": sid, "participant_id": pid})
    return pid


def test_consent_required(client):
    assert client.post("/api/participants", json={"consent": False}).status_code == 400


def test_missing_answers_rejected(client):
    p = client.post("/api/participants", json={"consent": True, "language": "en"}).get_json()
    r = client.post("/api/tests/pre", json={"participant_id": p["participant_id"], "responses": {"K01": "True"}})
    assert r.status_code == 400 and "Missing" in r.get_json()["error"]


def test_duplicate_answer_not_double_counted(client):
    p = client.post("/api/participants", json={"consent": True, "language": "en"}).get_json()
    q = client.post("/api/levels/1/start", json={"session_id": p["session_id"]}).get_json()["questions"][0]
    body = {"session_id": p["session_id"], "level": 1, "question_id": q["id"], "selected_option": "A"}
    first = client.post("/api/answer", json=body).get_json()
    second = client.post("/api/answer", json={**body, "selected_option": "B"}).get_json()
    assert first == second


def test_full_pilot_export_and_analysis(client, tmp_path):
    rng = random.Random(1)
    pids = [play_one(client, rng, finish=i % 4 != 0) for i in range(12)]
    play_one(client, rng, test_run=True)
    h = {"X-Admin-Token": TOKEN}
    pp = client.get("/api/admin/export/pre_post", headers=h).get_data(as_text=True)
    assert pp.count("\n") == 1 + len(pids)                 # test run excluded by default
    pp_all = client.get("/api/admin/export/pre_post?include_test=1", headers=h).get_data(as_text=True)
    assert pp_all.count("\n") == 2 + len(pids)
    r = client.post("/api/admin/analysis", headers=h, json={"include_test": False})
    assert r.status_code == 200, r.get_json()
    out = r.get_json()
    assert "Primary hypothesis" in out["summary"] and len(out["charts"]) == 5
    img = client.get(f"/api/admin/analysis/{out['run_id']}/charts/{out['charts'][0]}?token={TOKEN}")
    assert img.status_code == 200 and img.mimetype == "image/png"


def test_admin_requires_token(client):
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/admin/stats", headers={"X-Admin-Token": TOKEN}).status_code == 200


def test_review_and_unapproved_not_served(client, app):
    h = {"X-Admin-Token": TOKEN}
    qs = client.get("/api/admin/questions?level=1", headers=h).get_json()
    for q in qs[:-4]:
        assert client.post(f"/api/admin/questions/{q['question_id']}/review", headers=h,
                           json={"status": "rejected", "reviewer": "Tester"}).status_code == 200
    p = client.post("/api/participants", json={"consent": True, "language": "en"}).get_json()
    r = client.post("/api/levels/1/start", json={"session_id": p["session_id"]})
    assert r.status_code == 409          # only 4 approved left; level needs 5


def test_llm_drafts_are_checked_and_pending(client, app, monkeypatch):
    fake = [
        {"question_type": "tf", "question_en": "Antibiotics cure the flu.", "options_en": ["True", "False"],
         "explanation_en": "Flu is viral.", "hint_en": "Virus or bacteria?", "question_hi": "एंटीबायोटिक फ्लू ठीक करती हैं।",
         "options_hi": ["सही", "गलत"], "explanation_hi": "फ्लू वायरस से होता है।", "hint_hi": "वायरस या बैक्टीरिया?",
         "correct_index": 1, "fact_ids": ["F02"]},
        {"question_type": "mcq", "question_en": "How much amoxicillin should you take?", "options_en": ["500 mg", "a", "b", "c"],
         "explanation_en": "x", "hint_en": "x", "question_hi": "x", "options_hi": ["a", "b", "c", "d"],
         "explanation_hi": "x", "hint_hi": "x", "correct_index": 0, "fact_ids": ["F02"]},
    ]
    monkeypatch.setattr(llm, "call_gemini", lambda *a, **k: json.dumps(fake))
    h = {"X-Admin-Token": TOKEN}
    r = client.post("/api/admin/drafts", headers=h, json={"level": 1, "difficulty": "easy", "n": 2})
    res = r.get_json()
    assert r.status_code == 200, res
    assert res["n_inserted"] == 1 and res["n_failed_checks"] == 1
    qid = res["inserted_ids"][0]
    q = [x for x in client.get("/api/admin/questions?status=pending_review", headers=h).get_json()
         if x["question_id"] == qid][0]
    assert q["drafted_by"].startswith("LLM") and q["correct_answer"] == "B"
