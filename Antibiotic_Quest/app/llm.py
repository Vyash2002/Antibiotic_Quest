# -*- coding: utf-8 -*-
"""AI quiz module: draft new questions with Gemini, grounded ONLY in the verified fact base.

Drafts go into the questions table with review_status = 'pending_review'. They are never
shown to players until a reviewer approves them in the admin page.
"""
import json
import re
from datetime import datetime

import requests

from .content import LEVELS

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
LEVEL_TOPIC = {1: "T1_bacteria_vs_viruses", 2: "T2_antibiotic_misuse", 3: "T3_infection_prevention",
               4: "T4_amr", 5: None}

BANNED = re.compile(
    r"\b(\d+\s?mg|dose|dosage|tablets? a day|amoxicillin|azithromycin|ciprofloxacin|ofloxacin|cef\w+|"
    r"penicillin|doxycycline|metronidazole|finish the (whole )?course|complete the (full )?course|"
    r"stop when you feel better|you have (a|an) \w+ infection|diagnos\w+)\b", re.I)

PROMPT = """You write quiz questions for "Antibiotic Quest", a public-awareness game about antibiotic
resistance for adults in India.

RULES - follow all of them:
1. Use ONLY the facts provided below. Do not add any medical claim that is not in a fact.
2. Every question must cite the Fact_IDs it is based on.
3. Never name a specific medicine, brand or dose. Never suggest a diagnosis.
4. Never tell the player to start, stop or change a prescribed treatment on their own.
   The safe action is always "follow the prescription" or "ask a doctor or health worker".
5. Do not write "always finish the course" or "stop when you feel better".
   Use "take antibiotics exactly as prescribed" instead.
6. Use simple English (a 14-year-old should understand it). Indian names and settings are welcome.
7. Wrong options must be plausible misconceptions, not jokes.
8. Exactly one option is correct.
9. Also give a simple Hindi (Devanagari) translation of every text field, keeping the option order.
10. Do not repeat these existing questions: {existing}

FACTS:
{facts}

TASK: Write {n} questions for Level {level} ("{level_name}"), difficulty "{difficulty}".
Mix types: "tf" (true/false), "mcq" (4 options) and "scenario" (a short everyday story, 4 options).

Return ONLY a JSON array. Each element:
{{
  "question_type": "tf" | "mcq" | "scenario",
  "question_en": "...", "options_en": ["...", "..."], "explanation_en": "1-2 sentences", "hint_en": "short nudge",
  "question_hi": "...", "options_hi": ["...", "..."], "explanation_hi": "...", "hint_hi": "...",
  "correct_index": 0,
  "fact_ids": ["F07"]
}}
For "tf" use options_en ["True", "False"] and options_hi ["सही", "गलत"]; otherwise exactly 4 options.
"""


def build_prompt(db, level, difficulty, n):
    topic = LEVEL_TOPIC[level]
    sql = "SELECT fact_id, statement FROM facts WHERE use_in_game='yes'"
    args = ()
    if topic:
        sql += " AND topic=?"
        args = (topic,)
    facts = db.execute(sql, args).fetchall()
    existing = [r[0] for r in db.execute("SELECT question_en FROM questions WHERE level=?", (level,))]
    prompt = PROMPT.format(
        existing=json.dumps(existing[:40], ensure_ascii=False),
        facts="\n".join(f"{f['fact_id']} | {f['statement']}" for f in facts),
        n=n, level=level, level_name=LEVELS[level]["name"]["en"], difficulty=difficulty)
    return prompt, {f["fact_id"] for f in facts}


def call_gemini(prompt, api_key, model, timeout=90):
    r = requests.post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}},
        timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini API error {r.status_code}: {r.text[:400]}")
    data = r.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise RuntimeError("Gemini returned no text (it may have been blocked): " + json.dumps(data)[:400])
    return "".join(p.get("text", "") for p in parts)


def parse_drafts(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?|```$", "", text, flags=re.M).strip()
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("questions", [data])
    return [d for d in data if isinstance(d, dict)]


def check_draft(d, valid_fact_ids):
    errs = []
    qt = d.get("question_type")
    if qt not in ("tf", "mcq", "scenario"):
        return ["question_type"]
    n = 2 if qt == "tf" else 4
    for lang in ("en", "hi"):
        opts = d.get(f"options_{lang}") or []
        if len(opts) != n or not all(isinstance(o, str) and o.strip() for o in opts):
            errs.append(f"options_{lang}")
        for k in ("question", "explanation", "hint"):
            if not str(d.get(f"{k}_{lang}", "")).strip():
                errs.append(f"{k}_{lang}")
    ci = d.get("correct_index")
    if not isinstance(ci, int) or not 0 <= ci < n:
        errs.append("correct_index")
    fids = d.get("fact_ids") or []
    if not fids or set(fids) - valid_fact_ids:
        errs.append("fact_ids")
    text = " ".join(str(x) for x in [d.get("question_en"), d.get("explanation_en"), *(d.get("options_en") or [])])
    m = BANNED.search(text)
    if m:
        errs.append("banned term: " + m.group(0))
    return errs


def _next_draft_id(db):
    rows = db.execute("SELECT question_id FROM questions WHERE question_id LIKE 'AQD%'").fetchall()
    nums = [int(r[0][3:]) for r in rows if r[0][3:].isdigit()]
    return (max(nums) if nums else 0) + 1


def draft_questions(db, level, difficulty, n, api_key, model, caller=None):
    """Ask the LLM for n drafts, check them, insert survivors as pending_review. Returns a summary dict."""
    if level not in LEVEL_TOPIC or difficulty not in ("easy", "medium", "hard") or not 1 <= n <= 10:
        raise ValueError("level 1-5, difficulty easy/medium/hard, n 1-10")
    run = {"created_at": datetime.now().isoformat(timespec="seconds"), "model": model, "level": level,
           "difficulty": difficulty, "n_requested": n, "n_returned": 0, "n_failed_checks": 0, "n_inserted": 0,
           "error": None}
    inserted, rejected = [], []
    try:
        if not api_key:
            raise RuntimeError("No GEMINI_API_KEY set. Add it to the .env file and restart the server.")
        prompt, valid = build_prompt(db, level, difficulty, n)
        drafts = parse_drafts((caller or call_gemini)(prompt, api_key, model))
        run["n_returned"] = len(drafts)
        next_id = _next_draft_id(db)
        topic = LEVEL_TOPIC[level] or "T5_mixed_champion"
        for d in drafts:
            errs = check_draft(d, valid)
            if errs:
                rejected.append({"question_en": d.get("question_en", ""), "errors": errs})
                continue
            qt = d["question_type"]
            n_opt = 2 if qt == "tf" else 4
            oe = list(d["options_en"]) + [None] * (4 - n_opt)
            oh = list(d["options_hi"]) + [None] * (4 - n_opt)
            qid = f"AQD{next_id:03d}"
            next_id += 1
            db.execute(
                "INSERT INTO questions (question_id, level, topic, difficulty, question_type, question_en, "
                "option_a_en, option_b_en, option_c_en, option_d_en, explanation_en, hint_en, question_hi, "
                "option_a_hi, option_b_hi, option_c_hi, option_d_hi, explanation_hi, hint_hi, correct_answer, "
                "fact_ids, drafted_by, review_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (qid, level, topic, difficulty, qt, d["question_en"], *oe, d["explanation_en"], d["hint_en"],
                 d["question_hi"], *oh, d["explanation_hi"], d["hint_hi"], "ABCD"[d["correct_index"]],
                 ";".join(d["fact_ids"]), f"LLM ({model})", "pending_review"))
            inserted.append(qid)
        run["n_failed_checks"] = len(rejected)
        run["n_inserted"] = len(inserted)
    except Exception as e:  # noqa: BLE001 - every failure is logged and shown to the admin
        run["error"] = str(e)[:500]
    db.execute("INSERT INTO llm_runs (created_at, model, level, difficulty, n_requested, n_returned, "
               "n_failed_checks, n_inserted, error) VALUES (?,?,?,?,?,?,?,?,?)",
               (run["created_at"], model, level, difficulty, n, run["n_returned"], run["n_failed_checks"],
                run["n_inserted"], run["error"]))
    db.commit()
    return {**run, "inserted_ids": inserted, "rejected": rejected}
