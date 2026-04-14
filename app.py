from flask import Flask, request, jsonify
from openai import OpenAI
import yt_dlp
import requests
import json
import os

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# =====================
# 🎯 GET TRANSCRIPT FUNCTION
# =====================
def get_transcript_ytdlp(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "json3",  # 🔥 Force JSON3 format
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            subtitles = info.get("subtitles") or info.get("automatic_captions")

            if not subtitles:
                return None

            # Prefer English subtitles
            lang = "en" if "en" in subtitles else list(subtitles.keys())[0]

            sub_url = subtitles[lang][0]["url"]

            # Fetch subtitle file
            res = requests.get(sub_url)
            data = res.text

            # =====================
            # 🧠 PARSE JSON3 TRANSCRIPT
            # =====================
            try:
                json_data = json.loads(data)
            except Exception as e:
                print("JSON parse error:", e)
                return None

            clean_text = []

            for event in json_data.get("events", []):
                if "segs" in event:
                    for seg in event["segs"]:
                        text = seg.get("utf8", "").strip()
                        if text:
                            clean_text.append(text)

            return " ".join(clean_text)

    except Exception as e:
        print("Error:", e)
        return None

# =====================
# 🎯 AI FUNCTION
# =====================

# =====================
# 🎯 AI FUNCTIONS
# =====================

def generate_summary(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
You are an expert content summarizer.

Summarize the YouTube transcript in the following structured format:

🔹 Key Points:
- Use bullet points
- Keep each point short and clear

🔹 Main Ideas:
- Explain the core concept in simple words

🔹 Actionable Insights:
- Provide practical takeaways or actions

Keep the response clean, structured, and easy to read.
"""
                },
                {
                    "role": "user",
                    "content": text[:8000]
                }
            ],
            temperature=0.5
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI Error: {str(e)}"


# ✅ SEPARATE FUNCTION (FIXED)
def generate_keypoints(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
Extract only the most important key points from the transcript.

Rules:
- Use bullet points
- Keep each point very short (1 line)
- Max 8-10 points
- No extra explanation
"""
                },
                {
                    "role": "user",
                    "content": text[:8000]
                }
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI Error: {str(e)}"
    
# =====================
# 🌐 API ROUTE
# =====================
@app.route("/transcript")
def transcript():
    video_id = request.args.get("video_id")

    if not video_id:
        return jsonify({
            "success": False,
            "error": "Missing video_id"
        })

    transcript_text = get_transcript_ytdlp(video_id)

    if not transcript_text:
        return jsonify({
            "success": False,
            "transcript": "Transcript not available"
        })

    return jsonify({
        "success": True,
        "transcript": transcript_text
    })

@app.route("/summary")
def summary():
    video_id = request.args.get("video_id")

    if not video_id:
        return jsonify({"success": False})

    transcript = get_transcript_ytdlp(video_id)

    if not transcript:
        return jsonify({"success": False, "summary": "No transcript"})

    summary_text = generate_summary(transcript)

    return jsonify({
        "success": True,
        "summary": summary_text
    })

@app.route("/keypoints")
def keypoints():
    video_id = request.args.get("video_id")

    if not video_id:
        return jsonify({"success": False})

    transcript = get_transcript_ytdlp(video_id)

    if not transcript:
        return jsonify({
            "success": False,
            "keypoints": "No transcript available"
        })

    points = generate_keypoints(transcript)

    return jsonify({
        "success": True,
        "keypoints": points
    })

# =====================
# 🚀 RUN SERVER
# =====================
if __name__ == "__main__":
    app.run(port=5000, debug=True)