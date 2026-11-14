"""Export the database to the CSV formats used by analysis/analysis.py (data/templates/)."""
import csv
import io
import os

from .db import BANK_CSV, ROOT, read_csv

TEMPLATES = os.path.join(ROOT, "data", "templates")


def _template_header(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


def _where_real(include_test, alias="p"):
    return "" if include_test else f" AND {alias}.is_synthetic = 0"


def pre_post_rows(db, include_test=False):
    header = _template_header("Pre_Post_Test_Results_TEMPLATE.csv")
    parts = db.execute("SELECT * FROM participants p WHERE p.consent_given = 1" + _where_real(include_test)
                       + " ORDER BY p.participant_id").fetchall()
    rows = []
    for p in parts:
        resp = db.execute("SELECT phase, item_id, response, answered_at FROM test_responses WHERE participant_id=?",
                          (p["participant_id"],)).fetchall()
        r = {h: "" for h in header}
        r.update(participant_id=p["participant_id"], is_synthetic=p["is_synthetic"], consent_given="Y",
                 consent_timestamp=p["consent_timestamp"], D01=p["age_band"] or "", D02=p["gender"] or "",
                 D03=p["background"] or "", D04=p["prior_amr_teaching"] or "",
                 D05="Hindi" if p["language"] == "hi" else "English")
        times = {"pre": [], "post": []}
        for x in resp:
            times[x["phase"]].append(x["answered_at"])
            col = x["item_id"] if x["item_id"].startswith("FB") else f"{x['phase']}_{x['item_id']}"
            if col in r:
                r[col] = x["response"]
        r["pre_timestamp"] = min(times["pre"]) if times["pre"] else ""
        r["post_timestamp"] = min(times["post"]) if times["post"] else ""
        rows.append(r)
    return header, rows


def answer_log_rows(db, include_test=False):
    header = _template_header("Gameplay_Answer_Log_TEMPLATE.csv")
    q = ("SELECT e.*, p.is_synthetic FROM answer_events e JOIN participants p ON p.participant_id = e.participant_id "
         "WHERE 1=1" + _where_real(include_test) + " ORDER BY e.event_id")
    return header, [{h: r[h] for h in header} for r in db.execute(q)]


def gameplay_rows(db, include_test=False):
    header = _template_header("Gameplay_Analytics_TEMPLATE.csv")
    q = ("SELECT * FROM gameplay_analytics g WHERE 1=1" + _where_real(include_test, "g")
         + " ORDER BY participant_id, level")
    out = []
    for r in db.execute(q):
        d = {h: r[h] for h in header}
        d = {k: ("" if v is None else v) for k, v in d.items()}
        out.append(d)
    return header, out


def question_bank_rows(db, include_test=False):
    """Current questions (including reviews and LLM drafts) in AMR_Question_Bank.csv format."""
    header = list(read_csv(BANK_CSV)[0].keys())
    level_names = {1: "Know Your Enemy", 2: "The Antibiotic Trap", 3: "Stop the Spread",
                   4: "The Superbug Challenge", 5: "AMR Champion"}
    facts = {r["fact_id"]: r for r in db.execute("SELECT * FROM facts")}
    rows = []
    for q in db.execute("SELECT * FROM questions ORDER BY question_id"):
        fids = [f for f in (q["fact_ids"] or "").split(";") if f]
        orgs, urls = [], []
        for f in fids:
            if f in facts:
                for o in facts[f]["source_org"].split("; "):
                    if o not in orgs:
                        orgs.append(o)
                for u in facts[f]["source_url"].split("; "):
                    if u not in urls:
                        urls.append(u)
        d = {
            "Question_ID": q["question_id"], "Level": q["level"], "Level_Name": level_names[q["level"]],
            "Topic": q["topic"], "Difficulty": q["difficulty"], "Question_Type": q["question_type"],
            "Correct_Answer": q["correct_answer"], "Languages": "en;hi", "Fact_IDs": q["fact_ids"],
            "Source_Org": "; ".join(orgs), "Source_URL": "; ".join(urls), "Drafted_By": q["drafted_by"] or "",
            "Review_Status": q["review_status"], "Reviewer": q["reviewer"] or "",
            "Review_Date": q["review_date"] or "", "Review_Notes": q["review_notes"] or "",
        }
        for lang in ("EN", "HI"):
            l = lang.lower()
            d[f"Question_{lang}"] = q[f"question_{l}"] or ""
            for L in "ABCD":
                d[f"Option_{L}_{lang}"] = q[f"option_{L.lower()}_{l}"] or ""
            d[f"Explanation_{lang}"] = q[f"explanation_{l}"] or ""
            d[f"Hint_{lang}"] = q[f"hint_{l}"] or ""
        rows.append({h: d.get(h, "") for h in header})
    return header, rows


EXPORTS = {
    "pre_post": ("Pre_Post_Test_Results.csv", pre_post_rows),
    "answer_log": ("Gameplay_Answer_Log.csv", answer_log_rows),
    "gameplay": ("Gameplay_Analytics.csv", gameplay_rows),
    "question_bank": ("AMR_Question_Bank.csv", question_bank_rows),
}


def to_csv_text(header, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return "﻿" + buf.getvalue()      # BOM so Excel shows Hindi correctly


def write_all(db, folder, include_test=False):
    os.makedirs(folder, exist_ok=True)
    paths = {}
    for key, (fname, fn) in EXPORTS.items():
        header, rows = fn(db, include_test)
        path = os.path.join(folder, fname)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(to_csv_text(header, rows))
        paths[key] = path
    return paths

