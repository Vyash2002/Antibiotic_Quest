"""Create or update the Antibiotic Quest database.

Run from the project folder:
    python db/init_db.py                     # create db/antibiotic_quest.db if missing, add new questions
    python db/init_db.py --approve-all-demo  # mark every pending question approved (LOCAL TESTING ONLY)
    python db/init_db.py --reload-questions  # overwrite questions from data/AMR_Question_Bank.csv
                                             # (use after editing the CSV, e.g. one exported from /admin)
    python db/init_db.py --reset             # delete the database and start again (deletes ALL pilot data)
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.db import connect, init_schema, load_facts, load_questions  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("AQ_DATABASE", os.path.join(ROOT, "db", "antibiotic_quest.db")))
    ap.add_argument("--approve-all-demo", action="store_true")
    ap.add_argument("--reload-questions", action="store_true")
    ap.add_argument("--reset", action="store_true")
    a = ap.parse_args()

    if a.reset and os.path.exists(a.db):
        ans = input(f"Delete {a.db} and ALL participant data in it? Type 'yes': ")
        if ans.strip().lower() != "yes":
            print("Cancelled.")
            return
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(a.db + suffix):
                os.remove(a.db + suffix)

    os.makedirs(os.path.dirname(a.db), exist_ok=True)
    con = connect(a.db)
    init_schema(con)
    load_facts(con)
    changed = load_questions(con, reload=a.reload_questions, approve_all=a.approve_all_demo)
    n_q = con.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    n_ok = con.execute("SELECT COUNT(*) FROM playable_questions").fetchone()[0]
    n_f = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    con.close()
    print(f"{a.db}: {n_f} facts, {n_q} questions ({n_ok} approved / playable), {changed} rows changed")
    if a.approve_all_demo:
        print("WARNING: questions were auto-approved for local testing. Before the pilot, review them in /admin "
              "(or run --reset and review from scratch).")


if __name__ == "__main__":
    main()
