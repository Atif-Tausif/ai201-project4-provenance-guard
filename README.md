# Provenance Guard

A Flask REST API that detects whether submitted text is human-written or AI-generated. It runs two independent detection signals in sequence, combines their outputs into a single confidence score, and returns a transparency label explaining the result. Creators whose content is classified as AI-generated can file an appeal, which is recorded alongside the original classification decision in a structured audit log.

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Start the server:

```bash
python app.py
```

The server runs on `http://localhost:5000` by default.

---

## API Endpoints

### `POST /submit`

Accepts a JSON body with a text submission and returns a classification result.

**Request:**

```json
{
  "text": "The submitted content...",
  "creator_id": "some-user-id"
}
```

**Response:**

```json
{
  "content_id": "3f7a2b1e-...",
  "attribution": "likely_ai",
  "confidence": 0.7538,
  "label": {
    "title": "Likely AI-Generated",
    "message": "Our analysis indicates with high confidence that this content was generated using AI. This decision is based on multiple independent detection methods."
  },
  "llm_score": 0.85,
  "stylometric_score": 0.6576,
  "timestamp": "2025-04-01T14:32:10.123456+00:00"
}
```

**Rate limit:** 10 requests per minute, 100 per day per IP address.

---

### `POST /appeal`

Files an appeal on a previously classified submission.

**Request:**

```json
{
  "content_id": "3f7a2b1e-...",
  "creator_reasoning": "I wrote this myself. I am a non-native English speaker and my writing style may appear more formal than typical."
}
```

**Response:**

```json
{
  "message": "Appeal received. Your submission is now under review.",
  "content_id": "3f7a2b1e-...",
  "status": "under_review",
  "appeal_timestamp": "2025-04-01T14:45:00.000000+00:00"
}
```

---

### `GET /log`

Returns the 50 most recent audit log entries, newest first.

**Response:**

```json
{
  "entries": [
    {
      "content_id": "3f7a2b1e-...",
      "creator_id": "test-user-1",
      "timestamp": "2025-04-01T14:32:10.123456+00:00",
      "attribution": "likely_ai",
      "confidence": 0.7538,
      "llm_score": 0.85,
      "stylometric_score": 0.6576,
      "signals_agree": true,
      "label_title": "Likely AI-Generated",
      "status": "classified"
    }
  ]
}
```

---

## Detection Signals

### Signal 1: LLM-Based Classification (Groq)

The first signal sends the submitted text to Groq's `llama-3.3-70b-versatile` model with a prompt asking it to estimate the probability (0.0–1.0) that the text was AI-generated.

**Why this signal:** An LLM evaluates writing holistically — it can recognize AI-typical patterns like overly balanced phrasing, uniform paragraph structure, and the absence of personal voice in ways that rule-based heuristics cannot. It also generalizes across topics and writing styles without needing hand-tuned features per domain.

**What it actually produces:** Scores cluster toward the poles for clear cases. In testing, an obviously AI-generated paragraph about artificial intelligence scored 0.85–0.92 across multiple runs. A casual personal anecdote in informal register scored 0.20–0.21.

**Its real weakness:** The model tends to conflate "polished" with "AI-generated." A piece of professional academic writing scored 0.85 in testing, even though the stylometric signal found it structurally plausible as human writing (0.41). This isn't a calibration bug — it reflects a genuine property of the signal that cannot be tuned away without sacrificing sensitivity on actual AI output.

---

### Signal 2: Stylometric Analysis

The second signal measures four structural properties of the writing and combines them into a single score:

1. **Sentence-length variance (inverted):** AI text tends toward more uniform sentence lengths. Low variance → higher AI score. Calibrated against a typical human variance range of 20–100 words².
2. **Type-token ratio (inverted):** Measures vocabulary diversity relative to text length. AI output tends to use a narrower vocabulary set. Normalized to the expected TTR range of 0.4–0.8.
3. **Punctuation diversity (inverted):** Human writing uses a wider variety of punctuation marks (em-dashes, ellipses, exclamation points, parentheses). AI output skews toward periods and commas. Measured against a reference set of ten "rich" punctuation characters.
4. **Transition phrase density:** AI text overuses discourse connectors — "furthermore," "it is important to note," "stakeholders," "transformative." Measured as hits per 100 tokens against a 20-phrase lexicon.

**Why these four:** Each captures a distinct dimension of AI-writing behavior that is difficult to mask simultaneously. A writer who edits out transition phrases still tends to produce uniform sentence lengths; someone who varies sentence length rarely also diversifies their punctuation. The four metrics are largely independent, so their average is more stable than any single metric.

**What it actually produces:** In testing, the clearly AI paragraph scored 0.66 on stylometry while the informal human text scored 0.31. The formal academic text scored 0.41 — below the AI threshold — which is what allowed the agreement rule to catch it as `uncertain` rather than falsely classifying it as AI.

---

## Confidence Scoring

The final score is the simple average of both signals:

```
confidence = (llm_score + stylometric_score) / 2
```

**Thresholds:**

| Score range | Attribution |
|-------------|-------------|
| 0.00 – 0.45 | `likely_human` |
| 0.45 – 0.70 | `uncertain` |
| 0.70 – 1.00 | `likely_ai` |

**Agreement rule:** A `likely_ai` classification is only assigned when both signals independently land above 0.5. If one signal is above and the other below, the result is `uncertain` regardless of the average. This is the most important design decision in the scoring engine — it prevents a confident-but-wrong LLM score from overriding structural evidence that the writing is human.

**Why this approach:** Simple averaging with an agreement gate trades raw accuracy for fairness. The system will produce more `uncertain` results than a model optimized purely for classification accuracy, but it will produce fewer false positives on human writing. That tradeoff is intentional: incorrectly labeling a human creator's work as AI-generated has a direct reputational cost, while `uncertain` merely defers judgment.

**What I'd change for production:** The threshold boundaries (0.45, 0.70) were chosen conservatively based on manual testing but are not calibrated on a labeled dataset. In a real deployment I would collect ground-truth labels, plot a precision-recall curve for each threshold, and set the AI boundary wherever false-positive rate drops below an acceptable ceiling (something like 2%). I'd also weight the LLM score more heavily on short submissions (< 100 words), where the stylometric features become unreliable.

### Example submissions

**High-confidence AI** (formal AI-generated paragraph):

> *"Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders across various sectors must collaborate to ensure responsible deployment."*

```
llm_score:          0.85
stylometric_score:  0.66
confidence:         0.75
attribution:        likely_ai
signals_agree:      true
```

Both signals independently exceeded 0.5, so the agreement rule was satisfied and the result is `likely_ai`.

---

**Lower-confidence (uncertain) case** (formal human writing that splits the signals):

> *"The relationship between monetary policy and asset price inflation has been extensively studied in the literature. Central banks face a fundamental tension between their mandate for price stability and the unintended consequences of prolonged low interest rates on equity and real estate valuations."*

```
llm_score:          0.85
stylometric_score:  0.41
confidence:         0.63
attribution:        uncertain
signals_agree:      false
```

The LLM found this writing suspiciously polished; the stylometric analyzer found genuine sentence-length variation and natural punctuation. Because the two signals disagree, the agreement rule overrides the averaged score (which would otherwise be in the `likely_ai` range) and returns `uncertain`.

---

## Transparency Labels

The system returns one of three labels based on the final `attribution` value.

### Likely AI-Generated

Displayed when `attribution = "likely_ai"` (confidence ≥ 0.70, both signals agree):

> **Likely AI-Generated**
>
> Our analysis indicates with high confidence that this content was generated using AI. This decision is based on multiple independent detection methods.

---

### Likely Human-Written

Displayed when `attribution = "likely_human"` (confidence < 0.45):

> **Likely Human-Written**
>
> Our analysis indicates with high confidence that this content was written by a human. This decision is based on multiple independent detection methods.

---

### Uncertain

Displayed when `attribution = "uncertain"` (confidence in 0.45–0.70, or signals disagree):

> **Uncertain**
>
> Our analysis found mixed or inconclusive evidence. The system cannot confidently determine whether this content was AI-generated or human-written.

---

## Appeals Workflow

Any creator whose submission has been analyzed may file an appeal by sending a `POST /appeal` request with the `content_id` from their `/submit` response and a written explanation.

When an appeal is received, the system:

1. Looks up the original submission in the audit log.
2. Updates the submission entry's `status` from `"classified"` to `"under_review"` and adds `appeal_reasoning` and `appeal_timestamp` fields.
3. Appends a separate `appeal_filed` event to the log, preserving the full original classification alongside the appeal reason.
4. Returns a confirmation response.

No automatic reclassification occurs. The `GET /log` endpoint surfaces the appeal for human review.

---

## Rate Limiting

The `/submit` endpoint is limited to **10 requests per minute and 100 requests per day** per IP address.

**Reasoning:** A legitimate creator submitting their own work would rarely need more than a few classifications in a single minute. Ten per minute accommodates someone submitting multiple pieces back-to-back (a batch of essays, a day's work) without creating a meaningful window for automated flooding. The 100/day cap prevents overnight scripted abuse while leaving ample headroom for any realistic human usage pattern.

Requests exceeding the limit receive a `429 Too Many Requests` response.

**Rate limit test output** (12 rapid requests, showing first 10 succeed and 11–12 are rejected):

```
1  -> 200
2  -> 200
3  -> 200
4  -> 200
5  -> 200
6  -> 200
7  -> 200
8  -> 200
9  -> 200
10 -> 200
11 -> 429
12 -> 429
```

---

## Audit Log

Every `/submit` call writes a structured entry to `audit_log.jsonl` (one JSON object per line). Appeals update the original entry in-place and append a separate event record.

**Example entries:**

```json
{
  "content_id": "b53547de-3fb5-4fff-be47-fcd47aba53f0",
  "creator_id": "readme-demo-1",
  "timestamp": "2026-06-29T03:25:04.123456+00:00",
  "attribution": "likely_ai",
  "confidence": 0.7538,
  "llm_score": 0.85,
  "stylometric_score": 0.6576,
  "signals_agree": true,
  "label_title": "Likely AI-Generated",
  "status": "classified"
}
```

```json
{
  "content_id": "5e280ca0-fdc3-40c4-b545-145c42c50eb0",
  "creator_id": "readme-demo-2",
  "timestamp": "2026-06-29T03:25:15.234567+00:00",
  "attribution": "likely_human",
  "confidence": 0.2587,
  "llm_score": 0.21,
  "stylometric_score": 0.3075,
  "signals_agree": true,
  "label_title": "Likely Human-Written",
  "status": "classified"
}
```

```json
{
  "content_id": "ce217c82-34cb-4bd2-b3fc-0c51feb5615c",
  "creator_id": "readme-demo-3",
  "timestamp": "2026-06-29T03:25:26.345678+00:00",
  "attribution": "uncertain",
  "confidence": 0.6278,
  "llm_score": 0.85,
  "stylometric_score": 0.4055,
  "signals_agree": false,
  "label_title": "Uncertain",
  "status": "classified"
}
```

When an appeal is filed, two things happen: the original entry is mutated (status becomes `"under_review"`, `appeal_reasoning` and `appeal_timestamp` are added), and a new `appeal_filed` event is appended preserving the original classification details.

---

## Known Limitations

**Short submissions are unreliable.** Stylometric features break down below roughly 50–75 words. Sentence-length variance needs at least a handful of sentences to be meaningful; the type-token ratio is dominated by noise at short lengths. The system returns `uncertain` in these cases rather than a false classification, but it is genuinely uninformative rather than conservatively cautious. For a real deployment, submissions under ~75 words should be flagged upfront and either rejected or handled with a separate short-text classifier.

**Poetry and intentionally fragmented writing will score high on AI likelihood for the wrong reasons.** Short, repetitive lines with a narrow vocabulary and consistent punctuation are structurally indistinguishable from AI output to the stylometric analyzer. The LLM signal partially compensates — it can recognize creative register — but the stylometric score will pull the combined confidence up toward the `uncertain` zone even for clearly original creative work. This isn't a calibration problem; it's a fundamental property of stylometric features on non-prose text. A production system would need a separate detection path for identified creative writing.

**Heavily edited AI text defeats both signals.** If a creator takes AI-generated text and substantially rewrites sentence structure, adds personal anecdotes, and varies punctuation, both signals can drop below 0.5. The system would correctly return `uncertain` or even `likely_human`. This is partly by design — the system is not trying to prove AI involvement beyond reasonable doubt — but it means the recall on edited AI content is genuinely low, not just conservatively low.

---

## Spec Reflection

**Where the spec helped:** The agreement rule — requiring both signals to independently indicate AI before assigning `likely_ai` — came directly from the planning document and turned out to be the single most important implementation decision. Without it, the LLM's tendency to flag polished human writing would generate false positives at an unacceptable rate. The spec forced the architecture to account for signal disagreement before writing a line of code, which made the scoring logic straightforward to implement and test.

**Where implementation diverged:** The planning document described the stylometric signal as capturing sentence-length variance, vocabulary diversity, punctuation density, and sentence complexity. In implementation, "sentence complexity" was dropped and replaced with transition phrase density. Sentence complexity is difficult to measure meaningfully without a parse tree — heuristics like average clause count or subordination ratios are fragile on short inputs. Transition phrase density turned out to be far more discriminating in practice: real AI output reliably uses words like "furthermore," "stakeholders," and "transformative" at rates that human writing almost never matches. This was discovered during the standalone signal testing phase rather than the planning phase, and it changed the signal's character from a purely structural measure to one that also captures vocabulary register — which arguably makes it a stronger complement to the LLM signal.

---

## AI Tool Usage

This project used Claude (claude.ai/code) as an AI coding assistant throughout implementation. Two specific cases where the output required review and revision:

**1. Stylometric analyzer sub-scores**

I prompted the AI with the Detection Signals and architecture diagram sections of my planning document and asked it to implement the stylometric analyzer with sentence-length variance, type-token ratio, punctuation density, and sentence complexity. The AI produced a structurally correct implementation but used raw variance values with no normalization — a sentence-length variance of 30 was treated identically to one of 300, and both mapped to sub-scores near 0.5. This made the stylometric signal nearly constant across different inputs, which was not useful. I revised the implementation to normalize each sub-metric against a calibrated range (e.g., dividing sentence-length variance by 80.0 to map the expected human range of 20–100 onto 0–1), and replaced the sentence complexity metric with transition phrase density after finding the former too noisy on short inputs.

**2. Confidence scoring thresholds**

I prompted the AI with the Uncertainty Representation section and asked it to implement the scoring function that combines both signals. The AI produced a reasonable averaging function but implemented the agreement rule incorrectly: it required `abs(llm_score - stylometric_score) < 0.3` as the agreement condition, meaning signals that were both above 0.5 but separated by more than 0.3 would fail the agreement check. My spec defines agreement as both signals being on the same side of 0.5 — whether they point to AI or human — not as being numerically close to each other. I rewrote the agreement condition to `(llm_score >= 0.5) == (stylometric_score >= 0.5)`, which correctly captures the intent: both detectors must independently conclude the same direction. I verified this change against eight boundary cases before wiring the scorer into the endpoint.
