import os
import subprocess
import tempfile

import imageio_ffmpeg
import whisper
import whisper.audio
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Use the bundled ffmpeg
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd, *args, **kwargs):
    if cmd and "ffmpeg" in cmd[0]:
        cmd[0] = FFMPEG_PATH
    return subprocess.run(cmd, *args, **kwargs)


whisper.audio.run = run

# Load model once at startup
model = whisper.load_model("base")


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
    path = None
    try:
        audio = request.files["audio"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            audio.save(tmp.name)
            path = tmp.name

        result = model.transcribe(path, fp16=False)
        text = result.get("text", "")

        return jsonify({"risk": classify(text), "text": text})

    except Exception as e:
        return jsonify({"risk": "⚠️ ERROR", "text": str(e)}), 500

    finally:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
