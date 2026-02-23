"""
Automated test harness for Nova Voice Assistant.
Tests the full pipeline: text → fallback classifier → intent parser → router → TTS
"""

import os
import sys
import json
from pathlib import Path

# Ensure imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

from brain.fallback_classifier import fallback_classify
from brain.intent_parser import IntentParser
from brain.memory import Memory
from router.command_router import CommandRouter
from audio.text_to_speech import TextToSpeech

# ── Setup ──────────────────────────────────────────────────────────────────────
parser = IntentParser()
memory = Memory()
router = CommandRouter(memory)
tts    = TextToSpeech()

PASS = 0
FAIL = 0

def run_test(label: str, user_text: str, expect_intent: str = None,
             skip_route: bool = False):
    """Run one end-to-end test and print results."""
    global PASS, FAIL
    print(f"\n{'─'*60}")
    print(f"  TEST: {label}")
    print(f"  Input: \"{user_text}\"")

    # 1. Classify
    fb = fallback_classify(user_text)
    fb_json = json.dumps(fb) if fb else None
    classified_intent = fb.get("intent", "unknown") if fb else "unknown"
    print(f"  Classifier → intent={classified_intent}")

    # 2. Parse
    intent = parser.parse(fb_json, original_text=user_text)
    print(f"  Parser     → {intent}")

    # 3. Route (optionally skip for dangerous commands)
    if skip_route:
        response = "(skipped — dangerous command)"
    else:
        response = router.route(intent)
    print(f"  Router     → \"{response}\"")

    # 4. Check
    ok = True
    if expect_intent and intent.intent != expect_intent:
        ok = False
        print(f"  ❌ FAIL — Expected intent '{expect_intent}', got '{intent.intent}'")
    if not skip_route and (not response or response.strip() == ""):
        ok = False
        print(f"  ❌ FAIL — Empty response")

    if ok:
        PASS += 1
        print(f"  ✅ PASS")
    else:
        FAIL += 1

    return response


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("  Nova Voice Assistant — Automated Test Suite")
print("=" * 60)

# ── 1. Time ────────────────────────────────────────────────────────────────────
run_test("Time query",          "what time is it",            "time")
run_test("Time (alt phrasing)", "tell me the time",           "time")

# ── 2. Date ────────────────────────────────────────────────────────────────────
run_test("Date query",          "what is today's date",       "date")
run_test("Date (alt)",          "what day is it",             "date")

# ── 3. Greeting ────────────────────────────────────────────────────────────────
run_test("Greeting",            "hello",                      "greeting")
run_test("Greeting (alt)",      "hey",                        "greeting")

# ── 4. Open app ────────────────────────────────────────────────────────────────
run_test("Open Notepad",        "open notepad",               "open_app")

# ── 5. Close app ───────────────────────────────────────────────────────────────
run_test("Close Notepad",       "close notepad",              "close_app")

# ── 6. Search ──────────────────────────────────────────────────────────────────
run_test("Web search",          "search how to learn python", "search_web")
run_test("Search (alt)",        "look up weather today",      "search_web")

# ── 7. Volume ──────────────────────────────────────────────────────────────────
run_test("Set volume",          "set volume to 50",           "set_volume")
run_test("Volume (alt)",        "change volume to 30",        "set_volume")

# ── 8. Memory — save note ─────────────────────────────────────────────────────
run_test("Save note",           "remember buy milk tomorrow", "remember_note")

# ── 9. Memory — recall ────────────────────────────────────────────────────────
run_test("Recall notes",        "recall my notes",                      "recall_note")
run_test("Recall (alt)",        "what did I ask you to remember",       "recall_note")

# ── 10. System control (classify only — skip execution) ───────────────────────
run_test("Lock PC",             "lock the computer",          "lock_pc",   skip_route=True)
run_test("Shutdown",            "shut down the computer",     "shutdown",  skip_route=True)
run_test("Restart",             "restart the pc",             "restart",   skip_route=True)

# ── 11. Unknown input ─────────────────────────────────────────────────────────
run_test("Unknown input",       "flibbertigibbet",            "unknown")

# ── 12. Wake word stripping ───────────────────────────────────────────────────
import re
text = "hey nova open calculator"
cleaned = re.sub(r"^(?:hey\s+)?nova[\s,]*", "", text, flags=re.IGNORECASE).strip()
print(f"\n{'─'*60}")
print(f"  TEST: Wake word stripping")
print(f"  Input:   \"{text}\"")
print(f"  Cleaned: \"{cleaned}\"")
if cleaned == "open calculator":
    PASS += 1
    print(f"  ✅ PASS")
else:
    FAIL += 1
    print(f"  ❌ FAIL — expected 'open calculator'")

# ── 13. TTS smoke test ────────────────────────────────────────────────────────
print(f"\n{'─'*60}")
print(f"  TEST: TTS speaks a sentence")
try:
    tts.speak("Test complete. All systems operational.")
    PASS += 1
    print(f"  ✅ PASS — TTS spoke without error")
except Exception as e:
    FAIL += 1
    print(f"  ❌ FAIL — {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
print(f"{'='*60}")

# Cleanup
memory.close()
sys.exit(0 if FAIL == 0 else 1)
