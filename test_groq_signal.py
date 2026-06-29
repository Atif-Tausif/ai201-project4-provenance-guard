"""Quick standalone test for the Groq classifier — run before starting the server."""
from dotenv import load_dotenv
load_dotenv()

from signals.groq_classifier import classify_with_groq

samples = [
    ("human", "The sun dipped below the horizon, painting the sky in hues of amber and rose. "
              "I sat on the porch, coffee in hand, watching the neighborhood slowly go quiet."),
    ("ai",    "Artificial intelligence (AI) refers to the simulation of human intelligence processes "
              "by machines, particularly computer systems. These processes include learning, reasoning, "
              "and self-correction. AI applications include expert systems, natural language processing, "
              "speech recognition, and machine vision."),
    ("ambig", "Climate change is one of the most pressing issues of our time. "
              "Scientists agree that immediate action is needed to reduce carbon emissions."),
]

for label, text in samples:
    score = classify_with_groq(text)
    print(f"[{label:6s}] score={score:.3f}  text={text[:60]!r}...")
