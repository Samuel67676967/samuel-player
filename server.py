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
    "format": "bestaudio/best",
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

    stream_url = info.get("url")
    if not stream_url:
        # fall back to the best audio-only format explicitly, if present
        for fmt in info.get("formats", []):
            if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                stream_url = fmt.get("url")
                break

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
