# -*- coding: utf-8 -*-
"""Static game content: level metadata and the pre/post-test instrument."""
import functools
import os

from .db import ROOT, read_csv

INSTRUMENT_CSV = os.path.join(ROOT, "data", "Pre_Post_Test_Instrument.csv")

# Questions served per level. Level 5 mixes its own questions with earlier levels' ones.
QUESTIONS_PER_LEVEL = {1: 5, 2: 5, 3: 5, 4: 5, 5: 8}
LEVEL5_OWN = 4
BOARD_CELLS = 30

LEVELS = {
    1: {"name": {"en": "Know Your Enemy", "hi": "अपने दुश्मन को पहचानो"},
        "learn": {"en": "Antibiotics treat certain bacterial infections, not viral illnesses such as the common cold.",
                  "hi": "एंटीबायोटिक कुछ बैक्टीरियल संक्रमणों का इलाज करती हैं, सर्दी-ज़ुकाम जैसी वायरल बीमारियों का नहीं।"}},
    2: {"name": {"en": "The Antibiotic Trap", "hi": "एंटीबायोटिक का जाल"},
        "learn": {"en": "Spot the risky habits: self-medication, sharing medicines and using leftovers.",
                  "hi": "जोखिम भरी आदतें पहचानें: खुद से दवा लेना, दवा बाँटना और बची हुई दवा इस्तेमाल करना।"}},
    3: {"name": {"en": "Stop the Spread", "hi": "फैलाव रोको"},
        "learn": {"en": "Hand hygiene, vaccines and other everyday ways to prevent infections.",
                  "hi": "हाथों की सफ़ाई, टीके और संक्रमण से बचने के दूसरे रोज़मर्रा के तरीके।"}},
    4: {"name": {"en": "The Superbug Challenge", "hi": "सुपरबग चुनौती"},
        "learn": {"en": "What antimicrobial resistance is, why it is dangerous, and how it spreads.",
                  "hi": "रोगाणुरोधी प्रतिरोध क्या है, यह खतरनाक क्यों है और कैसे फैलता है।"}},
    5: {"name": {"en": "AMR Champion", "hi": "AMR चैंपियन"},
        "learn": {"en": "A final round that mixes everything you have learned.",
                  "hi": "आख़िरी दौर, जिसमें अब तक सीखी सारी बातें शामिल हैं।"}},
}


def _split(s):
    return [p.strip() for p in s.split("|")] if s else []


@functools.lru_cache(maxsize=1)
def instrument():
    """Return the test items grouped by section, with options in both languages.

    The stored value of an option is always language-independent (English label, 'A'-'D' or '1'-'5')
    so exports look the same whichever language the participant used.
    """
    out = {"demographics": [], "knowledge": [], "attitude": [], "feedback": []}
    for r in read_csv(INSTRUMENT_CSV):
        en, hi = _split(r["Response_Options_EN"]), _split(r["Response_Options_HI"])
        sec = r["Section"]
        item = {"id": r["Item_ID"], "section": sec, "topic": r["Topic"],
                "text": {"en": r["Item_EN"], "hi": r["Item_HI"]},
                "administered": r["Administered"], "options": [], "free_text": False,
                "required": sec in ("knowledge", "attitude")}
        if r["Response_Options_EN"] == "free text":
            item["free_text"] = True
        elif sec == "knowledge" and r["Correct_Response"] in ("A", "B", "C", "D"):
            for e, h in zip(en, hi):
                item["options"].append({"value": e[0], "label": {"en": e[2:].strip(), "hi": h[2:].strip()}})
        elif sec in ("attitude", "feedback"):
            for e, h in zip(en, hi):
                item["options"].append({"value": e.split(" ")[0], "label": {"en": e, "hi": h}})
        else:
            for e, h in zip(en, hi):
                item["options"].append({"value": e, "label": {"en": e, "hi": h}})
        if sec == "knowledge":
            item["key"] = r["Correct_Response"]
        if sec == "attitude":
            item["reverse"] = r["Reverse_Scored"] == "yes"
        out[sec].append(item)
    return out


def knowledge_key():
    return {it["id"]: it["key"] for it in instrument()["knowledge"]}


def public_instrument():
    """Instrument without answer keys (sent to the browser)."""
    pub = {}
    for sec, items in instrument().items():
        pub[sec] = [{k: v for k, v in it.items() if k not in ("key", "reverse")} for it in items]
    return pub
