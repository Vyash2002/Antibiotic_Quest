"""Pre-generate narration MP3s for the questions (optional - the game falls back to the
browser's built-in voice when a file is missing).

Needs internet and the gTTS package:
    pip install gTTS
    python tools/generate_audio.py               # approved questions, English + Hindi
    python tools/generate_audio.py --all         # every question, including pending ones
    python tools/generate_audio.py --lang hi     # Hindi only

Writes app/static/audio/<lang>/<QID>_q.mp3 (question + options) and <QID>_e.mp3 (explanation),
plus app/static/audio/manifest.json, which the game reads at start-up. Existing files are skipped
unless you pass --overwrite. Ask a native speaker to listen to a sample of the Hindi files.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.db import connect  # noqa: E402

AUDIO = os.path.join(ROOT, "app", "static", "audio")


def spoken_question(q, lang):
    letters = "AB" if q["question_type"] == "tf" else "ABCD"
    opts = " ".join(f"{l}. {q[f'option_{l.lower()}_{lang}'] or q[f'option_{l.lower()}_en']}." for l in letters)
    return f"{q[f'question_{lang}'] or q['question_en']} {opts}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="+", default=["en", "hi"], choices=["en", "hi"])
    ap.add_argument("--all", action="store_true", help="include questions that are not approved yet")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--db", default=os.environ.get("AQ_DATABASE", os.path.join(ROOT, "db", "antibiotic_quest.db")))
    a = ap.parse_args()
    try:
        from gtts import gTTS
    except ImportError:
        sys.exit("gTTS is not installed. Run:  pip install gTTS")

    con = connect(a.db)
    table = "questions" if a.all else "playable_questions"
    qs = con.execute(f"SELECT * FROM {table} ORDER BY question_id").fetchall()
    if not qs:
        sys.exit("No questions found. Approve questions first or use --all.")

    manifest_path = os.path.join(AUDIO, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8")) if os.path.exists(manifest_path) else {}
    for lang in a.lang:
        os.makedirs(os.path.join(AUDIO, lang), exist_ok=True)
        manifest.setdefault(lang, {})
        for i, q in enumerate(qs, 1):
            jobs = {f"{q['question_id']}_q": spoken_question(q, lang),
                    f"{q['question_id']}_e": q[f"explanation_{lang}"] or q["explanation_en"]}
            for key, text in jobs.items():
                rel = f"audio/{lang}/{key}.mp3"
                path = os.path.join(AUDIO, lang, f"{key}.mp3")
                if os.path.exists(path) and not a.overwrite:
                    manifest[lang][key] = rel
                    continue
                for attempt in range(3):
                    try:
                        kwargs = {"lang": lang}
                        if lang == "en":
                            kwargs["tld"] = "co.in"   # Indian English accent
                        gTTS(text, **kwargs).save(path)
                        manifest[lang][key] = rel
                        break
                    except Exception as e:  # noqa: BLE001 - network hiccups / rate limits
                        print(f"  retry {key} ({e})")
                        time.sleep(2 + attempt * 3)
                time.sleep(0.3)
            print(f"[{lang}] {i}/{len(qs)} {q['question_id']}")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=1)
    print(f"Done. Manifest: {manifest_path}. Restart run.py (or reload the page) to use the files.")


if __name__ == "__main__":
    main()
