import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # allow the PWA (hosted on a different origin) to call this API

COOKIE_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")
_cookie_opts = {"cookiefile": COOKIE_FILE} if os.path.exists(COOKIE_FILE) else {}

YDL_SEARCH_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "skip_download": True,
    "default_search": "ytsearch",
    **_cookie_opts,
}

YDL_STREAM_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
    **_cookie_opts,
}


@app.get("/")
def health():
    return jsonify({"status": "ok", "service": "samuels-player-backend"})


@app.get("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    with yt_dlp.YoutubeDL(YDL_SEARCH_OPTS) as ydl:
        info = ydl.extract_info(f"ytsearch8:{q}", download=False)

    results = []
    for entry in info.get("entries", []):
        if not entry:
            continue
        results.append({
            "id": entry.get("id"),
            "title": entry.get("title"),
            "artist": entry.get("uploader") or entry.get("channel"),
            "duration": entry.get("duration"),
        })
    return jsonify(results)


@app.get("/stream/<video_id>")
def stream(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    with yt_dlp.YoutubeDL(YDL_STREAM_OPTS) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats", []) or []

    def has_audio(f):
        return f.get("acodec") and f.get("acodec") != "none"

    def has_video(f):
        return f.get("vcodec") and f.get("vcodec") != "none"

    # Prefer audio-only formats (smallest download, exactly what we need).
    audio_only = [f for f in formats if has_audio(f) and not has_video(f)]
    # Fall back to combined audio+video formats.
    combined = [f for f in formats if has_audio(f) and has_video(f)]

    def bitrate(f):
        return f.get("abr") or f.get("tbr") or 0

    chosen = None
    if audio_only:
        chosen = max(audio_only, key=bitrate)
    elif combined:
        chosen = max(combined, key=bitrate)
    elif info.get("url"):
        chosen = info

    if not chosen or not chosen.get("url"):
        return jsonify({"error": "could not resolve stream", "available_formats": len(formats)}), 404

    return jsonify({
        "url": chosen.get("url"),
        "title": info.get("title"),
        "artist": info.get("uploader"),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
