# Detection Signals

Our system uses two independent detection signals to determine whether a piece of text is more likely to be human-written or AI-generated.

## Signal 1: LLM-Based Classification (Groq)

The first signal uses the Groq API with the `llama-3.3-70b-versatile` model. The model analyzes the writing holistically, considering semantic coherence, writing style, organization, tone, and linguistic patterns. Rather than relying on measurable statistics alone, the LLM evaluates whether the overall writing resembles typical AI-generated or human-written content.

The model returns a confidence score between **0.0 and 1.0**, where **0.0** indicates the text is very likely human-written and **1.0** indicates it is very likely AI-generated.

**Strengths**

* Captures subtle stylistic and semantic patterns.
* Understands context rather than isolated writing statistics.

**Limitations**

* Can be overly confident.
* May incorrectly classify highly polished human writing, professional journalism, or heavily edited essays as AI-generated.

---

## Signal 2: Stylometric Analysis

The second signal uses stylometric heuristics implemented in Python. Rather than interpreting meaning, it measures structural characteristics of the writing, including:

* Sentence length variance
* Vocabulary diversity (type-token ratio)
* Punctuation density
* Average sentence complexity

Human writing generally exhibits greater variation in these characteristics, while AI-generated text often appears more uniform and consistent.

The stylometric analyzer also returns a score between **0.0 and 1.0**, where **0.0** represents writing that appears more human and **1.0** represents writing that appears more AI-like.

**Strengths**

* Provides an objective, measurable signal.
* Independent from the LLM-based classifier.

**Limitations**

* Cannot understand context or meaning.
* Performs poorly on very short submissions, poetry, or intentionally simplified writing.

---

## Combining the Signals

The final AI likelihood score is computed by averaging the outputs of the two detection signals:

```text
Final Score = (Groq Score + Stylometric Score) / 2
```

Although the average determines the overall score, the system also considers **agreement between the two signals**. A high-confidence AI classification is only assigned when both detectors independently indicate that the writing is likely AI-generated. If the detectors strongly disagree, the submission is classified as **Uncertain**, even if the average score is relatively high. This reduces the likelihood of falsely labeling human-written work as AI-generated.

---

# Uncertainty Representation

The final confidence score represents the estimated probability that the submitted text was AI-generated.

For example:

* **0.20** indicates strong evidence that the text is human-written.
* **0.50** indicates that the evidence is mixed and the system cannot confidently determine authorship.
* **0.85** indicates strong evidence that the text is AI-generated.

Because false positives (incorrectly labeling human-written work as AI-generated) are considered more harmful than false negatives, the system uses **conservative decision thresholds**.

| Score Range     | Classification        |
| --------------- | --------------------- |
| **0.00 – 0.45** | High Confidence Human |
| **0.45 – 0.70** | Uncertain             |
| **0.70 – 1.00** | High Confidence AI    |

Additionally, a submission is only labeled as **High Confidence AI** when both detection signals independently support an AI classification. Mixed evidence results in an **Uncertain** label instead of an AI attribution.

---

# Transparency Label Design

The platform presents users with one of three transparency labels.

### High Confidence AI

> **Likely AI-Generated**
>
> Our analysis indicates with high confidence that this content was generated using AI. This decision is based on multiple independent detection methods.

---

### High Confidence Human

> **Likely Human-Written**
>
> Our analysis indicates with high confidence that this content was written by a human. This decision is based on multiple independent detection methods.

---

### Uncertain

> **Uncertain**
>
> Our analysis found mixed or inconclusive evidence. The system cannot confidently determine whether this content was AI-generated or human-written.

---

# Appeals Workflow

Any creator whose submission has been analyzed may submit an appeal.

The appeal includes:

* Submission ID
* Written explanation describing why they believe the classification is incorrect

When an appeal is submitted, the system:

1. Records the appeal reason.
2. Updates the submission status from **Completed** to **Under Review**.
3. Creates a new audit log entry linking the appeal to the original attribution decision.
4. Returns confirmation that the appeal has been received.

A human reviewer viewing the appeal queue would see:

* Submission ID
* Original submitted text
* Original classification
* Final confidence score
* Individual Groq score
* Individual stylometric score
* Transparency label shown to the user
* Appeal reason provided by the creator
* Timestamp of both the original decision and the appeal

No automatic reclassification is performed after an appeal is submitted.

---

# Anticipated Edge Cases

## 1. Highly Polished Human Writing

Professional authors, journalists, or academic writers may produce writing that is exceptionally consistent and well-structured. The LLM classifier may identify these characteristics as AI-like even though the work is entirely human-written. The stylometric signal may still indicate human writing, resulting in an **Uncertain** classification rather than a false AI attribution.

---

## 2. Poetry and Creative Writing

Poetry often uses repetition, unconventional grammar, short sentences, and limited vocabulary intentionally. These characteristics may resemble AI-generated writing according to stylometric heuristics, even when the work is entirely original.

---

## 3. AI Text That Has Been Heavily Edited

A creator may substantially rewrite AI-generated text by changing sentence structure, vocabulary, and punctuation. These edits can make the writing appear more human according to stylometric analysis while still appearing AI-like to the LLM. The disagreement between the two signals may result in an **Uncertain** classification.

---

## 4. Very Short Submissions

Short passages provide limited information for both detectors. Stylometric features become unreliable with very little text, and the LLM has less context to analyze. As a result, the system may be unable to confidently classify the submission and will likely return an **Uncertain** result.

## Architecture

### Submission Flow

```text
                    POST /submit
                          │
                          │ Raw text
                          ▼
                  Rate Limiter
                          │
                          │ Allowed request
                          ▼
                 Input Validation
                          │
                          │ Validated text
                          ▼
            ┌───────────────────────────┐
            │   Groq LLM Classifier      │
            │  → AI likelihood score     │
            └───────────────────────────┘
                          │
                          │ Groq score (0–1)
                          ▼
            ┌───────────────────────────┐
            │  Stylometric Analyzer     │
            │ → Structural AI score     │
            └───────────────────────────┘
                          │
                          │ Stylometric score (0–1)
                          ▼
             Confidence Scoring Engine
      (Average both signals and evaluate agreement)
                          │
                          │ Final confidence score
                          ▼
          Transparency Label Generator
      (Human / Uncertain / AI transparency label)
                          │
                          │ Classification + label
                          ▼
                     Audit Log
      (Stores submission, scores, label,
       timestamps, and appeal status)
                          │
                          │ Response payload
                          ▼
                    JSON Response
```

---

### Appeal Flow

```text
                    POST /appeal
                          │
                          │ Submission ID + Appeal Reason
                          ▼
                 Validate Submission
                          │
                          ▼
              Update Submission Status
                  → "Under Review"
                          │
                          │ Updated status + appeal
                          ▼
                     Audit Log
       (Records appeal reason, timestamp,
        original decision, and new status)
                          │
                          ▼
                 JSON Confirmation
```


# Milestone 3 (Submission Endpoint + First Signal)

For Milestone 3, I will provide the AI coding tool with the **Detection Signals** section and the **architecture diagram** from my planning document. These sections describe the purpose of the Groq-based classifier, the expected score format (0.0–1.0), and how the submission endpoint fits into the overall system architecture.

I will ask the AI tool to generate:

* A Flask application skeleton.
* A `POST /submit` endpoint that accepts a JSON payload containing submitted text.
* Input validation for empty or invalid submissions.
* A Groq API integration that returns an AI likelihood score between 0.0 and 1.0.
* A structured JSON response containing the submission ID and the first detection signal's output.

Before integrating the endpoint with the remainder of the pipeline, I will verify the Groq classifier independently using several pieces of sample text, including clearly human-written passages, AI-generated text, and ambiguous examples. The goal is to ensure the endpoint correctly communicates with the API and consistently returns valid confidence scores.

---

# Milestone 4 (Second Signal + Confidence Scoring)

For Milestone 4, I will provide the AI coding tool with the **Detection Signals**, **Uncertainty Representation**, and **architecture diagram** sections of the planning document.

I will ask the AI tool to generate:

* A stylometric analysis module that computes features such as sentence length variance, vocabulary diversity, punctuation density, and sentence complexity.
* A function that converts those measurements into a normalized AI likelihood score between 0.0 and 1.0.
* Confidence scoring logic that averages the Groq and stylometric scores while applying the conservative decision thresholds defined in the planning document.
* Logic that only assigns a high-confidence AI classification when both detection signals independently indicate AI-generated writing. Otherwise, mixed evidence should result in an **Uncertain** classification.

To verify the implementation, I will test the system using a collection of clearly human-written passages, clearly AI-generated passages, and intentionally ambiguous examples. I will confirm that the combined confidence scores vary meaningfully between these cases and that disagreements between the two signals produce an **Uncertain** result rather than an incorrect AI classification.

---

# Milestone 5 (Production Layer)

For Milestone 5, I will provide the AI coding tool with the **Transparency Label Design**, **Appeals Workflow**, and **architecture diagram** sections of the planning document.

I will ask the AI tool to generate:

* Logic that maps the final confidence score and classification to one of the three transparency labels.
* A `POST /appeal` endpoint that accepts a submission ID and an appeal reason.
* Audit log functionality that records the original attribution decision, confidence scores, transparency label, appeal reason, timestamps, and status updates.
* Logic that updates a submission's status from **Completed** to **Under Review** after an appeal is submitted.

To verify the implementation, I will test all three transparency label variants by submitting texts that should produce high-confidence human, uncertain, and high-confidence AI classifications. I will also submit an appeal and verify that the submission status changes to **Under Review**, the appeal is recorded in the audit log, and the original attribution decision remains available for review.
