import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # allow the PWA (hosted on a different origin) to call this API

YDL_SEARCH_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "skip_download": True,
}

YDL_STREAM_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
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
        info = ydl.extract_info(f"scsearch8:{q}", download=False)

    results = []
    for entry in info.get("entries", []):
        if not entry:
            continue
        track_url = entry.get("webpage_url") or entry.get("url")
        if not track_url:
            continue
        results.append({
            "id": track_url,
            "title": entry.get("title"),
            "artist": entry.get("uploader") or entry.get("channel"),
            "duration": entry.get("duration"),
        })
    return jsonify(results)


@app.get("/stream/<path:track_url>")
def stream(track_url):
    with yt_dlp.YoutubeDL(YDL_STREAM_OPTS) as ydl:
        info = ydl.extract_info(track_url, download=False)

    formats = info.get("formats", []) or []

    def has_audio(f):
        return f.get("acodec") and f.get("acodec") != "none"

    def bitrate(f):
        return f.get("abr") or f.get("tbr") or 0

    audio_formats = [f for f in formats if has_audio(f)]
    chosen = max(audio_formats, key=bitrate) if audio_formats else None
    stream_url = chosen.get("url") if chosen else info.get("url")

    if not stream_url:
        return jsonify({"error": "could not resolve stream"}), 404

    return jsonify({
        "url": stream_url,
        "title": info.get("title"),
        "artist": info.get("uploader"),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
