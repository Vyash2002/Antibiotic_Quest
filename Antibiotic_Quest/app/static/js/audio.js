// Audio narration. Uses pre-generated MP3s from tools/generate_audio.py when they exist,
// otherwise the browser's built-in speech (Web Speech API). Text is always shown on screen too.

let manifest = {};          // { "hi": { "AQ001_q": "audio/hi/AQ001_q.mp3", ... }, "en": {...} }
let current = null;         // currently playing HTMLAudioElement
let voices = [];

export function initAudio(audioFiles) {
  manifest = audioFiles || {};
  if ("speechSynthesis" in window) {
    const load = () => { voices = window.speechSynthesis.getVoices(); };
    load();
    window.speechSynthesis.onvoiceschanged = load;
  }
}

function pickVoice(lang) {
  const want = lang === "hi" ? ["hi-IN", "hi"] : ["en-IN", "en-GB", "en-US", "en"];
  for (const w of want) {
    const v = voices.find((x) => x.lang && x.lang.replace("_", "-").toLowerCase().startsWith(w.toLowerCase()));
    if (v) return v;
  }
  return null;
}

export function hasVoice(lang) {
  return Boolean((manifest[lang] && Object.keys(manifest[lang]).length) || pickVoice(lang));
}

export function stop() {
  if (current) { current.pause(); current = null; }
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

/** Speak `text` in `lang`. `key` (e.g. "AQ001_q") selects a pre-generated file if one exists.
 *  Resolves true if something played, false if no voice is available. */
export function speak(text, lang, key) {
  stop();
  const file = key && manifest[lang] && manifest[lang][key];
  if (file) {
    return new Promise((resolve) => {
      current = new Audio("/static/" + file);
      current.onended = () => resolve(true);
      current.onerror = () => resolve(speakSynth(text, lang));
      current.play().catch(() => resolve(speakSynth(text, lang)));
    });
  }
  return Promise.resolve(speakSynth(text, lang));
}

function speakSynth(text, lang) {
  if (!("speechSynthesis" in window)) return false;
  const voice = pickVoice(lang);
  if (!voice) return false;
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.lang = voice.lang;
  u.rate = lang === "hi" ? 0.95 : 1.0;
  window.speechSynthesis.speak(u);
  return true;
}
