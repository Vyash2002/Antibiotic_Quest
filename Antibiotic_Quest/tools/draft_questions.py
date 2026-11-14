"""Draft new questions with Gemini from the command line (same as the admin page's AI drafts tab).

    python tools/draft_questions.py --level 2 --difficulty medium --n 3

Needs GEMINI_API_KEY in .env (and optionally GEMINI_MODEL). Drafts are added as pending_review.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import load_env_file  # noqa: E402
from app.db import connect, ensure_database  # noqa: E402
from app.llm import draft_questions  # noqa: E402


def main():
    load_env_file(os.path.join(ROOT, ".env"))
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--difficulty", default="medium", choices=["easy", "medium", "hard"])
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--db", default=os.environ.get("AQ_DATABASE", os.path.join(ROOT, "db", "antibiotic_quest.db")))
    a = ap.parse_args()
    ensure_database(a.db)
    con = connect(a.db)
    res = draft_questions(con, a.level, a.difficulty, a.n, os.environ.get("GEMINI_API_KEY", ""),
                          os.environ.get("GEMINI_MODEL", "gemini-flash-latest"))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    con.close()


if __name__ == "__main__":
    main()
