import os

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Groq's free tier accepts files up to 25 MB
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "whisper-large-v3-turbo")


def transcribe(file_storage):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("The server is missing its GROQ_API_KEY setting.")

    name = file_storage.filename or "audio.webm"
    data = file_storage.read()

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": "Bearer " + key},
        files={"file": (name, data, file_storage.mimetype or "application/octet-stream")},
        data={"model": GROQ_MODEL, "response_format": "json"},
        timeout=120,
    )
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text)
        except ValueError:
            msg = resp.text
        raise RuntimeError("Transcription failed (%s): %s" % (resp.status_code, msg))
    return resp.json().get("text", "")


def classify(text):
    text = (text or "").lower()
    if any(x in text for x in ["otp", "cvv", "pin", "share otp"]):
        return "🚨 FRAUD"
    if any(x in text for x in ["bank", "kyc", "urgent", "account blocked"]):
        return "⚠️ SUSPICIOUS"
    return "✅ SAFE"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        if "audio" not in request.files:
            return jsonify({"risk": "⚠️ ERROR", "text": "No audio was received."}), 400
        text = transcribe(request.files["audio"])
        return jsonify({"risk": classify(text), "text": text})
    except Exception as e:
        return jsonify({"risk": "⚠️ ERROR", "text": str(e)}), 500


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"risk": "⚠️ ERROR", "text": "That file is too large. The limit is 25 MB."}), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
