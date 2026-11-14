"""Generate SYNTHETIC pilot data so you can build and test the analysis pipeline
before real participants play.

!!! These numbers are invented. Never report them as findings. !!!
Every row has is_synthetic = 1 and the files are prefixed SYNTHETIC_.

Usage (from the package folder):
    python analysis/make_synthetic_data.py --n 40 --seed 7
"""
import argparse, os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "synthetic"))
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    os.makedirs(a.out, exist_ok=True)

    inst = pd.read_csv(os.path.join(ROOT, "data", "Pre_Post_Test_Instrument.csv"), keep_default_na=False)
    qb = pd.read_csv(os.path.join(ROOT, "data", "AMR_Question_Bank.csv"), keep_default_na=False)
    know = inst[inst.Section == "knowledge"]
    att = inst[inst.Section == "attitude"]

    # item "difficulty" for the simulation only
    item_b = {k: rng.normal(-0.2, 0.9) for k in know.Item_ID}
    for hard in ("K13", "K14", "K04", "K08"):        # known misconception items: harder at baseline
        item_b[hard] += 1.0

    t0 = datetime(2026, 11, 20, 10, 0)
    pp_rows, log_rows, lvl_rows = [], [], []
    ev = 0
    for i in range(1, a.n + 1):
        pid = f"P{i:03d}"
        theta = rng.normal(0, 1)
        delta = max(0.0, rng.normal(1.1, 0.6))       # learning from the game
        lang = rng.choice(["en", "hi"], p=[0.6, 0.4])
        start = t0 + timedelta(minutes=int(rng.integers(0, 60 * 24 * 5)))
        row = dict(participant_id=pid, is_synthetic=1, consent_given="Y",
                   consent_timestamp=start.isoformat(timespec="seconds"),
                   D01=rng.choice(["18-21", "22-25", "26-30"], p=[0.3, 0.55, 0.15]),
                   D02=rng.choice(["Woman", "Man", "Prefer not to say"], p=[0.4, 0.55, 0.05]),
                   D03=rng.choice(["Computer science / IT", "Other engineering", "Biology / health sciences", "Other"],
                                  p=[0.6, 0.2, 0.1, 0.1]),
                   D04=rng.choice(["Yes", "No", "Not sure"], p=[0.2, 0.6, 0.2]),
                   D05="English" if lang == "en" else "Hindi",
                   pre_timestamp=start.isoformat(timespec="seconds"))

        for phase, boost in (("pre", 0.0), ("post", delta)):
            for _, it in know.iterrows():
                k, key = it.Item_ID, it.Correct_Response
                ok = rng.random() < sigmoid(theta + boost - item_b[k])
                if k == "K09":
                    resp = "C" if ok else rng.choice(["A", "B", "D"], p=[0.5, 0.2, 0.3])
                else:
                    wrong = "False" if key == "True" else "True"
                    resp = key if ok else (wrong if rng.random() < 0.65 else "Don't know")
                row[f"{phase}_{k}"] = resp
            for _, it in att.iterrows():
                prudent = np.clip(np.round(rng.normal(3.2 + 0.4 * theta + 0.5 * boost, 0.9)), 1, 5)
                row[f"{phase}_{it.Item_ID}"] = int(6 - prudent if it.Reverse_Scored == "yes" else prudent)

        # ---- gameplay
        session = f"S{i:03d}"
        t = start + timedelta(minutes=6)
        levels_done = 0
        for level in range(1, 6):
            if level > 1 and rng.random() > 0.93:     # some players quit
                break
            pool = qb[qb.Level == level]
            if level == 5:
                qs = pd.concat([pool, qb[qb.Level < 5].sample(4, random_state=int(rng.integers(1e9)))])
            else:
                qs = pool.sample(5, random_state=int(rng.integers(1e9)))
            lvl_start = t
            n_ok = n_hint = pts = 0
            for _, q in qs.iterrows():
                b = {"easy": -1.0, "medium": 0.0, "hard": 0.9}[q.Difficulty]
                hint = int(rng.random() < 0.15)
                p = sigmoid(theta + 0.3 * level / 5 + 0.6 * hint - b)
                ok = rng.random() < p
                n_opts = 2 if q.Question_Type == "tf" else 4
                opts = list("ABCD"[:n_opts])
                wrong_opts = [o for o in opts if o != q.Correct_Answer]
                sel = q.Correct_Answer if ok else rng.choice(wrong_opts, p=None if len(wrong_opts) == 1 else
                                                              [0.6, 0.25, 0.15][:len(wrong_opts)])
                rt = int(rng.lognormal(np.log(9000), 0.45))
                t += timedelta(milliseconds=rt + 4000)
                ev += 1
                points = (10 - 3 * hint) if ok else 0
                pts += points
                n_ok += ok
                n_hint += hint
                log_rows.append(dict(event_id=ev, participant_id=pid, session_id=session, is_synthetic=1,
                                     level=level, question_id=q.Question_ID, language=lang, attempt_no=1,
                                     selected_option=sel, correct_option=q.Correct_Answer, is_correct=int(ok),
                                     hint_used=hint, audio_played=int(rng.random() < (0.7 if lang == "hi" else 0.3)),
                                     response_time_ms=rt, points_awarded=points,
                                     timestamp=t.isoformat(timespec="seconds")))
            levels_done = level
            lvl_rows.append(dict(participant_id=pid, session_id=session, is_synthetic=1, level=level,
                                 questions_attempted=len(qs), correct=n_ok, incorrect=len(qs) - n_ok,
                                 hints_used=n_hint, time_spent_sec=int((t - lvl_start).total_seconds()),
                                 points=pts, level_completed=1, audio_used=int(lang == "hi"), language=lang,
                                 started_at=lvl_start.isoformat(timespec="seconds"),
                                 ended_at=t.isoformat(timespec="seconds")))
        post_t = t + timedelta(minutes=2)
        row["post_timestamp"] = post_t.isoformat(timespec="seconds")
        for fb in ("FB01", "FB02", "FB03", "FB04"):
            row[fb] = int(np.clip(np.round(rng.normal(4.0, 0.8)), 1, 5))
        row["FB05"] = ""
        pp_rows.append(row)

    tmpl = pd.read_csv(os.path.join(ROOT, "data", "templates", "Pre_Post_Test_Results_TEMPLATE.csv"))
    pd.DataFrame(pp_rows)[list(tmpl.columns)].to_csv(
        os.path.join(a.out, "SYNTHETIC_Pre_Post_Test_Results.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(log_rows).to_csv(os.path.join(a.out, "SYNTHETIC_Gameplay_Answer_Log.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(lvl_rows).to_csv(os.path.join(a.out, "SYNTHETIC_Gameplay_Analytics.csv"), index=False, encoding="utf-8-sig")
    print(f"wrote synthetic data for {a.n} participants to {a.out} (NOT real results)")


if __name__ == "__main__":
    main()
