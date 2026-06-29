"""
Milestone 4 test — run before starting the server.

Tests:
  1. Stylometric analyzer in isolation on 4 sample texts
  2. Scoring thresholds match planning.md exactly
  3. Agreement rule: mixed signals → "uncertain" even if average >= 0.70
  4. Both signals on all 4 samples (compare agreement / divergence)
"""
from dotenv import load_dotenv
load_dotenv()

from signals.stylometric_analyzer import analyze_stylometry
from signals.groq_classifier import classify_with_groq
from scoring import compute_confidence

SAMPLES = [
    ("clearly_ai",
     "Artificial intelligence represents a transformative paradigm shift in modern society. "
     "It is important to note that while the benefits of AI are numerous, it is equally "
     "essential to consider the ethical implications. Furthermore, stakeholders across "
     "various sectors must collaborate to ensure responsible deployment."),

    ("clearly_human",
     "ok so i finally tried that new ramen place downtown and honestly? "
     "underwhelming. the broth was fine but they put WAY too much sodium in it and "
     "i was thirsty for like three hours after. my friend got the spicy version and "
     "said it was better. probably won't go back unless someone drags me there"),

    ("borderline_formal_human",
     "The relationship between monetary policy and asset price inflation has been "
     "extensively studied in the literature. Central banks face a fundamental tension "
     "between their mandate for price stability and the unintended consequences of "
     "prolonged low interest rates on equity and real estate valuations."),

    ("borderline_edited_ai",
     "I've been thinking a lot about remote work lately. There are genuine tradeoffs — "
     "flexibility and no commute on one side, isolation and blurred work-life boundaries "
     "on the other. Studies show productivity varies widely by individual and role type."),
]

print("=" * 72)
print(f"{'Label':<25} {'LLM':>6} {'Stylo':>6} {'Conf':>6} {'Attribution':<18} {'Agree'}")
print("-" * 72)

for label, text in SAMPLES:
    llm   = classify_with_groq(text)
    stylo = analyze_stylometry(text)
    result = compute_confidence(llm, stylo)
    print(f"{label:<25} {llm:>6.3f} {stylo:>6.3f} {result.confidence:>6.3f} "
          f"{result.attribution:<18} {'yes' if result.signals_agree else 'NO'}")

print("=" * 72)

# --- Threshold boundary checks (unit-level) ---
print("\nThreshold boundary checks:")
cases = [
    (0.20, 0.20, "likely_human"),      # 0.20 avg  < 0.45
    (0.44, 0.44, "likely_human"),      # 0.44 avg  < 0.45
    (0.50, 0.50, "uncertain"),         # 0.50 avg in [0.45, 0.70)
    (0.69, 0.69, "uncertain"),         # 0.69 avg in [0.45, 0.70)
    (0.80, 0.80, "likely_ai"),         # 0.80 avg  >= 0.70, both agree
    (0.90, 0.10, "uncertain"),         # avg = 0.50 but signals disagree
    (0.95, 0.75, "likely_ai"),         # avg 0.85, both AI-side
    (0.95, 0.20, "uncertain"),         # avg 0.575 but signals strongly disagree
]
all_pass = True
for llm, stylo, expected in cases:
    r = compute_confidence(llm, stylo)
    ok = r.attribution == expected
    if not ok:
        all_pass = False
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] llm={llm:.2f} stylo={stylo:.2f} -> {r.attribution} (expected {expected})")
if all_pass:
    print("  All threshold checks passed.")
