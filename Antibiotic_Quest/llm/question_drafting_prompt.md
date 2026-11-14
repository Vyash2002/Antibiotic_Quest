# AI quiz module: grounded question-drafting prompt

> The app implements this pipeline in `app/llm.py` (admin page → AI drafts, or `tools/draft_questions.py`).
> This file documents the prompt and checks for your report.

Use this prompt with Gemini or any other LLM when you want *new* questions. The LLM is only
allowed to rephrase facts from `data/AMR_Facts.csv`. It never invents medical content, and
every draft goes into the bank as `pending_review`. Count how many drafts reviewers approve;
the project plan lists that number as a technical-quality metric.

## Pipeline

1. Pick facts where `Use_In_Game = yes` (e.g. all facts for one topic).
2. Fill the prompt below with those facts (ID + statement only) and the target level/difficulty.
3. Ask for JSON output and validate it against the schema (reject anything that fails).
4. Run the automatic safety checks (below). Drop drafts that fail.
5. Append surviving drafts to `AMR_Question_Bank.csv` with
   `Drafted_By = "LLM (<model name>)"`, `Review_Status = pending_review`.
6. A reviewer marks each one `approved`, `needs_edit` or `rejected`. Only `approved` rows are served
   (the `playable_questions` view in `db/schema.sql`).

## Prompt

```
You write quiz questions for "Antibiotic Quest", a public-awareness game about antibiotic
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

FACTS:
{facts}            # one line per fact: F07 | Only use antibiotics when they are prescribed by ...

TASK: Write {n} questions for Level {level} ({level_name}), difficulty {difficulty}.
Mix types: "tf" (true/false), "mcq" (4 options) and "scenario" (a short everyday story, 4 options).

Return ONLY a JSON array. Each element:
{
  "question_type": "tf" | "mcq" | "scenario",
  "question_en": "...",
  "options_en": ["...", "..."],          # 2 for tf (["True","False"]), 4 otherwise
  "correct_index": 0,
  "explanation_en": "1-2 sentences, why the answer is right, based only on the cited facts",
  "hint_en": "short nudge that does not give the answer away",
  "fact_ids": ["F07"]
}
```

For Hindi, run a second call that translates `question_en`, `options_en`, `explanation_en`
and `hint_en` into simple Hindi (Devanagari), keeping option order. A native speaker must
check the translation.

## Automatic checks before a draft reaches a reviewer

```python
import json, re
BANNED = re.compile(r"\b(mg|dose|dosage|tablet[s]? a day|amoxicillin|azithromycin|ciprofloxacin|"
                    r"cef\w+|penicillin|finish the (whole )?course|stop when you feel better|"
                    r"you have (a|an) \w+ infection|diagnos\w+)\b", re.I)

def check(draft, valid_fact_ids):
    errs = []
    n = 2 if draft["question_type"] == "tf" else 4
    if len(draft["options_en"]) != n: errs.append("option count")
    if not 0 <= draft["correct_index"] < n: errs.append("correct_index")
    if not draft["fact_ids"] or set(draft["fact_ids"]) - valid_fact_ids: errs.append("fact_ids")
    text = " ".join([draft["question_en"], draft["explanation_en"], *draft["options_en"]])
    if BANNED.search(text): errs.append("banned term: " + BANNED.search(text).group(0))
    return errs
```

The regex is a coarse filter, not a safety guarantee. The human review is the real check.
Log how many drafts each stage removes so you can report it.
