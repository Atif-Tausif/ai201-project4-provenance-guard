import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from signals.groq_classifier import classify_with_groq
from signals.stylometric_analyzer import analyze_stylometry
from scoring import compute_confidence
from labels import generate_label
from audit import append_log_entry, get_log_entries, get_entry_by_content_id, update_entry_status

load_dotenv()

app = Flask(__name__)

# Rate limit rationale: a real creator submitting their own work would rarely send
# more than a few pieces per minute. 10/minute prevents scripted flooding while
# comfortably accommodating legitimate use; 100/day caps sustained automation.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400

    text = body.get("text", "").strip()
    creator_id = body.get("creator_id", "").strip()

    if not text:
        return jsonify({"error": "Field 'text' is required and must not be empty"}), 400
    if not creator_id:
        return jsonify({"error": "Field 'creator_id' is required and must not be empty"}), 400

    content_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    llm_score = classify_with_groq(text)
    stylometric_score = analyze_stylometry(text)
    result = compute_confidence(llm_score, stylometric_score)
    label = generate_label(result.attribution)

    entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": timestamp,
        "attribution": result.attribution,
        "confidence": result.confidence,
        "llm_score": result.llm_score,
        "stylometric_score": result.stylometric_score,
        "signals_agree": result.signals_agree,
        "label_title": label.title,
        "status": "classified",
    }
    append_log_entry(entry)

    return jsonify({
        "content_id": content_id,
        "attribution": result.attribution,
        "confidence": result.confidence,
        "label": {
            "title": label.title,
            "message": label.message,
        },
        "llm_score": result.llm_score,
        "stylometric_score": result.stylometric_score,
        "timestamp": timestamp,
    }), 200


@app.route("/appeal", methods=["POST"])
def appeal():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400

    content_id = body.get("content_id", "").strip()
    reasoning = body.get("creator_reasoning", "").strip()

    if not content_id:
        return jsonify({"error": "Field 'content_id' is required"}), 400
    if not reasoning:
        return jsonify({"error": "Field 'creator_reasoning' is required"}), 400

    original = get_entry_by_content_id(content_id)
    if original is None:
        return jsonify({"error": f"No submission found with content_id '{content_id}'"}), 404

    if original.get("status") == "under_review":
        return jsonify({"error": "An appeal has already been filed for this submission"}), 409

    appeal_timestamp = datetime.now(timezone.utc).isoformat()

    updated = update_entry_status(
        content_id,
        new_status="under_review",
        extra_fields={
            "appeal_reasoning": reasoning,
            "appeal_timestamp": appeal_timestamp,
        },
    )
    if not updated:
        return jsonify({"error": "Failed to update submission status"}), 500

    # Append a separate appeal event so the timeline is fully preserved
    appeal_event = {
        "event": "appeal_filed",
        "content_id": content_id,
        "appeal_timestamp": appeal_timestamp,
        "appeal_reasoning": reasoning,
        "original_attribution": original.get("attribution"),
        "original_confidence": original.get("confidence"),
        "original_label_title": original.get("label_title"),
        "original_llm_score": original.get("llm_score"),
        "original_stylometric_score": original.get("stylometric_score"),
        "original_timestamp": original.get("timestamp"),
        "status": "under_review",
    }
    append_log_entry(appeal_event)

    return jsonify({
        "message": "Appeal received. Your submission is now under review.",
        "content_id": content_id,
        "status": "under_review",
        "appeal_timestamp": appeal_timestamp,
    }), 200


@app.route("/log", methods=["GET"])
def log():
    entries = get_log_entries()
    return jsonify({"entries": entries}), 200


if __name__ == "__main__":
    app.run(debug=True)
