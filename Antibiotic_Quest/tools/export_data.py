"""Export the pilot data to CSV (same as the admin page's Data tab).

    python tools/export_data.py                 # writes exports/latest/*.csv (real participants only)
    python tools/export_data.py --include-test  # also team test runs (IDs starting with T)
    python tools/export_data.py --out data      # write straight into data/ for analysis/analysis.py
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.db import connect  # noqa: E402
from app.exports import write_all  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "exports", "latest"))
    ap.add_argument("--include-test", action="store_true")
    ap.add_argument("--db", default=os.environ.get("AQ_DATABASE", os.path.join(ROOT, "db", "antibiotic_quest.db")))
    a = ap.parse_args()
    con = connect(a.db)
    paths = write_all(con, a.out, a.include_test)
    con.close()
    for k, p in paths.items():
        print(f"{k:14s} {p}")


if __name__ == "__main__":
    main()
