# Antibiotic Quest 
# Computing For Medicine(CSE585)

A browser-based snakes-and-ladders game that teaches responsible antibiotic use. It measures
learning with a pre-test/post-test design. Computing for Medicine project, IIIT-Delhi.

- **Frontend:** HTML, CSS, JavaScript and Phaser 3 (bundled, works offline). English and Hindi, with audio narration.
- **Backend:** Python Flask with a SQLite database. Data is anonymous (IDs like P001).
- **AI module:** Gemini drafts new questions, but only from the verified fact base, and a person reviews every draft.
- **Analysis:** paired t-test or Wilcoxon, effect size, and topic, item and gameplay results with charts. You can run it from the admin page.

---

## 1. Run it (5 minutes)

You need Python 3.9 or newer. Open a terminal **inside this folder**.

**WSL / Linux / Mac**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # then edit ADMIN_TOKEN (and GEMINI_API_KEY if you have one)
python db/init_db.py --approve-all-demo    # ONLY for trying it out - see section 3
python run.py
```

**Windows (Command Prompt / PowerShell)**
```bat
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python db\init_db.py --approve-all-demo
python run.py
```

Then open **http://localhost:5000** for the game and **http://localhost:5000/admin** for the
admin page. The admin password is `ADMIN_TOKEN` in `.env`; it defaults to `change-me`.

**Playing on phones during the pilot:** run `python run.py --host 0.0.0.0`. The terminal prints
an address such as `http://192.168.1.23:5000` that phones on the same Wi-Fi can open. On WSL,
phones may not reach the server. If so, run it from Windows Python instead, or see
Troubleshooting.

## 2. What the player sees

1. **Welcome:** choose English or हिंदी and turn sound on or off.
2. **Consent:** a plain explanation, optional demographics, and an "I agree" checkbox. Tick "Team test run"
   when you are testing. Those players get IDs starting with **T** and are left out of exports.
3. **Pre-test:** 16 knowledge items and 6 attitude items, in random order. Every item must be answered.
4. **Five levels** (Know Your Enemy → The Antibiotic Trap → Stop the Spread → The Superbug
   Challenge → AMR Champion). Each level is a 30-square board:
   - Roll the die to move. A **superbug** sits on some squares and blocks the way, so you must answer its
     question to get past (5 per level, 8 in Level 5).
   - **Correct:** the superbug turns green, you climb a ladder of 3 squares and earn 10 points (7 if you used the hint).
   - **Wrong:** the explanation and the right answer appear, and the superbug's snake slides you back 3 squares.
   - The **Listen** button reads the question aloud. Answers are checked on the server, so the
     browser never has the answer key.
   - Players can stop early ("End game and take the final quiz").
5. **Post-test:** the same items, reshuffled, plus 5 feedback questions.
6. **Results:** the player's before and after scores, four key messages and their participant ID.

Refreshing the page resumes at the current level, and already-answered questions are not counted twice.

## 3. Before the pilot (required)

- [ ] **Remove the demo approvals.** `--approve-all-demo` marks all 56 questions as approved without review
      (the admin page warns about this). For the real pilot run `python db/init_db.py --reset`. This
      deletes the database, including test data. Then review the questions properly.
- [ ] **Medical review.** In **/admin → Review questions**, a faculty member or clinician checks each question
      against its cited fact and approves it, marks it "Needs edit" or rejects it. Only approved questions are
      served. Levels 1-4 each need at least 5 approved questions; Level 5 needs 4.
- [ ] **Hindi review.** The Hindi text is an AI draft, so a native speaker should read it, ideally aloud.
- [ ] **Re-check dated facts.** These are the WHO GLASS 2025 figures, NAP-AMR 2.0 and World AMR Awareness Week 2026
      (questions AQ047-AQ051 and AQ055-AQ056).
- [ ] **Change `ADMIN_TOKEN`** in `.env`.
- [ ] **Test the whole flow** with "Team test run" ticked, on the phones and laptops you will use.

**To change a question's wording:** in **/admin → Data and analysis**, download "Question bank (with
reviews)". Edit it in Excel, save it as `data/AMR_Question_Bank.csv` (CSV UTF-8), and run
`python db/init_db.py --reload-questions`.

## 4. After the pilot: data and analysis

**/admin → Data and analysis**
- Download the three datasets from the project plan: pre/post test results, the gameplay answer log, and
  gameplay analytics (one row per player per level).
- **Run analysis** exports the data and runs `analysis/analysis.py`. It shows the summary and 5 charts and
  saves everything in `exports/<date_time>/`.

Or from the terminal:
```bash
python tools/export_data.py --out exports/latest
python analysis/analysis.py --prepost exports/latest/Pre_Post_Test_Results.csv \
  --log exports/latest/Gameplay_Answer_Log.csv --levels exports/latest/Gameplay_Analytics.csv --out results
python analysis/analysis.py --power-only        # sample-size table for the Hypothesis slide
```

Pre-registered analysis, in `analysis/analysis.py`: H0 μpost = μpre vs H1 μpost > μpre, α = 0.05. The
primary test is a paired t-test if the differences pass Shapiro-Wilk, otherwise Wilcoxon signed-rank.
It reports Cohen's dz with a bootstrap CI. Topic, item, attitude and engagement results are secondary
and Holm-adjusted. You need about 27 participants for dz = 0.5; recruit 35-45.

`data/synthetic/` holds **invented** data for 40 fake players, for testing the pipeline only. Charts
made from it are stamped SYNTHETIC.

## 5. AI question drafting (optional)

1. Get a Gemini API key at https://aistudio.google.com/apikey and put it in `.env` as `GEMINI_API_KEY=...`.
   `GEMINI_MODEL` defaults to `gemini-flash-latest`.
2. Restart `run.py`, then open **/admin → AI drafts**. Pick a level, difficulty and number, then click
   **Draft questions**.
3. The model may only use that level's facts from `data/AMR_Facts.csv`. Drafts that name a medicine, give a
   dose, diagnose, use the "finish the course" wording, cite unknown facts or have the wrong number of options
   are rejected automatically. The rest are added as **pending review**.
4. Review them like any other question. The Overview tab shows *AI-drafted questions approved*, the plan's
   technical-quality metric. Each run is logged in the "Recent runs" table.

Command-line version: `python tools/draft_questions.py --level 2 --difficulty medium --n 3`.

## 6. Audio narration

By default the game uses the browser's built-in voice. Chrome and Edge on Windows usually include a Hindi
voice; if a device has none, the game says so and the text stays on screen. For consistent, better
audio, pre-generate MP3s (this needs internet):
```bash
pip install gTTS
python tools/generate_audio.py            # approved questions, English + Hindi
```
The files go to `app/static/audio/` and the game uses them automatically.

## 7. Project structure

```
Antibiotic_Quest/
├── run.py                  start the server
├── requirements.txt, .env.example
├── app/
│   ├── __init__.py         Flask app factory, .env loading
│   ├── api.py              player API: participants, tests, levels, answers, results
│   ├── admin.py            admin API: review, AI drafts, exports, analysis runner
│   ├── llm.py              Gemini drafting + safety checks
│   ├── exports.py          DB → CSV in the analysis formats
│   ├── content.py          level texts, test instrument loader
│   ├── db.py               SQLite helpers, CSV loading
│   ├── templates/          index.html (game), admin.html
│   └── static/
│       ├── js/             main.js (game flow), board.js (Phaser board), audio.js, api.js, i18n.js, admin.js
│       ├── css/            game.css, admin.css
│       ├── vendor/         phaser.min.js (MIT licence)
│       ├── fonts/          Baloo 2 + Mukta, Latin + Devanagari (SIL OFL)
│       └── audio/          generated narration (optional)
├── db/                     schema.sql, init_db.py (database file is created here)
├── data/                   question bank, fact base, test instrument, CSV templates, synthetic data
├── analysis/               analysis.py, make_synthetic_data.py, sample output (synthetic)
├── llm/                    the grounded prompt, documented
├── tools/                  export_data.py, draft_questions.py, generate_audio.py
├── tests/                  end-to-end tests  (pip install pytest; python -m pytest -q)
└── SOURCES_AND_DATASETS.md external datasets and references
```

**Database tables:** `participants`, `test_responses`, `game_sessions`, `level_progress`, `answer_events`,
`questions`, `facts` and `llm_runs`. The view `gameplay_analytics` is Dataset 3, and `playable_questions`
contains only approved questions.

## 8. Content and safety decisions

- **Antibiotic course length.** The game says "take antibiotics exactly as prescribed and ask your doctor
  before stopping". It never says "always finish the course" or "stop when you feel better", because that
  message is contested (Llewelyn et al., BMJ 2017;358:j3418). CDC and WHO public materials use "as prescribed".
- **No drug names, doses or diagnoses.** The safe answer is always to follow the prescription or see a doctor
  or health worker. The consent screen says the game is not medical advice.
- **Grounded content.** Every question cites a fact in `data/AMR_Facts.csv`, and every fact links to WHO, CDC,
  MoHFW/ICMR or the GRAM study.
- **Privacy.** No names, phone numbers or emails are collected; demographics are optional.

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| "Level 1 needs 5 approved questions…" | Approve questions in /admin, or for a local test run `python db/init_db.py --approve-all-demo` |
| `ModuleNotFoundError: flask` | Activate the venv and run `pip install -r requirements.txt` |
| `Address already in use` | Another copy is running. Close it, or use `python run.py --port 5001` |
| Page is blank or "server didn't respond" | Check that `run.py` is still running in the terminal |
| Phones can't open the game | Use `--host 0.0.0.0`, put the phones on the same Wi-Fi, and allow Python through the firewall. On WSL2, either run from Windows Python, or forward the port from an admin PowerShell: `netsh interface portproxy add v4tov4 listenport=5000 listenaddress=0.0.0.0 connectport=5000 connectaddress=<WSL IP>` |
| No Hindi voice | Use Chrome or Edge, or generate MP3s (section 6) |
| Gemini error 404 (model not found) | Set `GEMINI_MODEL` in `.env` to a current model name |
| Excel shows Hindi as garbled characters | Open the CSV with Data → From Text/CSV and choose UTF-8 |
| "database is locked" / slow on WSL | The project is on a Windows or OneDrive folder (`/mnt/c/...`). Copy it into your WSL home (`cp -r ... ~/Antibiotic_Quest`) and run it there; OneDrive syncing a live database also causes locks |
| Start over | `python db/init_db.py --reset` (deletes all data) |
