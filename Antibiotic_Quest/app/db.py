"""SQLite helpers: connection per request, schema creation and CSV loading."""
import csv
import os
import sqlite3

from flask import current_app, g

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "db", "schema.sql")
FACTS_CSV = os.path.join(ROOT, "data", "AMR_Facts.csv")
BANK_CSV = os.path.join(ROOT, "data", "AMR_Question_Bank.csv")
DEMO_REVIEWER = "DEMO auto-approval (not reviewed)"

QUESTION_COLS = [
    "question_id", "level", "topic", "difficulty", "question_type",
    "question_en", "option_a_en", "option_b_en", "option_c_en", "option_d_en", "explanation_en", "hint_en",
    "question_hi", "option_a_hi", "option_b_hi", "option_c_hi", "option_d_hi", "explanation_hi", "hint_hi",
    "correct_answer", "fact_ids", "drafted_by", "review_status", "reviewer", "review_date", "review_notes",
]


def connect(path):
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def init_schema(con):
    """Create tables (idempotent) and migrate databases made by older kit versions."""
    con.execute("DROP VIEW IF EXISTS gameplay_analytics")
    con.execute("DROP VIEW IF EXISTS playable_questions")
    with open(SCHEMA, encoding="utf-8") as f:
        con.executescript(f.read())
    cols = [r[1] for r in con.execute("PRAGMA table_info(level_progress)")]
    if "question_ids" not in cols:
        con.execute("ALTER TABLE level_progress ADD COLUMN question_ids TEXT NOT NULL DEFAULT ''")
    con.commit()


def load_facts(con, path=FACTS_CSV):
    con.execute("DELETE FROM facts")
    con.executemany(
        "INSERT INTO facts VALUES (?,?,?,?,?,?)",
        [(r["Fact_ID"], r["Topic"], r["Statement"], r["Source_Org"], r["Source_URL"], r["Use_In_Game"])
         for r in read_csv(path)])
    con.commit()


def _bank_row_to_tuple(r, approve_all):
    status = r.get("Review_Status") or "pending_review"
    reviewer = r.get("Reviewer")
    if approve_all and status == "pending_review":
        status, reviewer = "approved", DEMO_REVIEWER
    blank = lambda v: v if v not in ("", None) else None
    return (r["Question_ID"], int(r["Level"]), r["Topic"], r["Difficulty"], r["Question_Type"],
            r["Question_EN"], r["Option_A_EN"], r["Option_B_EN"], blank(r["Option_C_EN"]), blank(r["Option_D_EN"]),
            r["Explanation_EN"], r["Hint_EN"],
            r["Question_HI"], r["Option_A_HI"], r["Option_B_HI"], blank(r["Option_C_HI"]), blank(r["Option_D_HI"]),
            r["Explanation_HI"], r["Hint_HI"],
            r["Correct_Answer"], r["Fact_IDs"], r.get("Drafted_By"), status,
            blank(reviewer), blank(r.get("Review_Date")), blank(r.get("Review_Notes")))


def load_questions(con, path=BANK_CSV, reload=False, approve_all=False):
    """Load the question bank CSV.

    Default: insert only questions that are not in the database yet, so reviews done in the
    admin page are kept. reload=True overwrites every question with the CSV (use after you
    edit the CSV, e.g. one exported from the admin page).
    """
    rows = read_csv(path)
    placeholders = ", ".join("?" * len(QUESTION_COLS))
    if reload:
        sql = (f"INSERT INTO questions ({', '.join(QUESTION_COLS)}) VALUES ({placeholders}) "
               "ON CONFLICT(question_id) DO UPDATE SET "
               + ", ".join(f"{c}=excluded.{c}" for c in QUESTION_COLS[1:]))
    else:
        sql = f"INSERT OR IGNORE INTO questions ({', '.join(QUESTION_COLS)}) VALUES ({placeholders})"
    before = con.total_changes
    con.executemany(sql, [_bank_row_to_tuple(r, approve_all) for r in rows])
    if approve_all:
        con.execute("UPDATE questions SET review_status='approved', reviewer=? WHERE review_status='pending_review'",
                    (DEMO_REVIEWER,))
    con.commit()
    return con.total_changes - before


def ensure_database(path):
    """Create the database on first run (questions start as pending_review)."""
    fresh = not os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = connect(path)
    init_schema(con)
    if fresh or con.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0:
        load_facts(con)
    if con.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0:
        load_questions(con)
    n_ok = con.execute("SELECT COUNT(*) FROM playable_questions").fetchone()[0]
    con.close()
    return fresh, n_ok


def init_app(app):
    app.teardown_appcontext(close_db)
