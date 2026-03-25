from flask import Flask, request, Response, render_template, jsonify, send_file, abort
import yt_dlp
import os
import uuid
import threading

app = Flask(__name__)

USERNAME = os.environ.get("APP_USERNAME", "admin")
PASSWORD = os.environ.get("APP_PASSWORD", "admin")

progress_store: dict = {}

ALLOWED_URL_PREFIXES = (
    "https://www.youtube.com/",
    "https://youtu.be/",
    "https://youtube.com/",
    "https://m.youtube.com/",
)
ALLOWED_QUALITIES = {"360", "480", "720", "1080", "1440", "2160"}


def check_auth(username, password):
    return username == USERNAME and password == PASSWORD


@app.before_request
def require_login():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return Response(
            'Login Required', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )


@app.route('/')
def home():
    return render_template("index.html")


def make_progress_hook(session_id):
    def progress_hook(d):
        if d['status'] == 'downloading':
            raw = d.get('_percent_str', '0%').replace('%', '').strip()
            try:
                progress_store[session_id]["percent"] = float(raw)
                progress_store[session_id]["status"] = "downloading"
                progress_store[session_id]["speed"] = d.get('_speed_str', '')
                progress_store[session_id]["eta"] = d.get('_eta_str', '')
            except ValueError:
                pass
        elif d['status'] == 'finished':
            progress_store[session_id]["percent"] = 99
            progress_store[session_id]["status"] = "processing"
    return progress_hook


@app.route('/progress/<session_id>')
def progress(session_id):
    data = progress_store.get(session_id, {"percent": 0, "status": "idle"})
    return jsonify(data)


@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url', '').strip()
    format_type = request.form.get('format', 'mp4')
    quality = request.form.get('quality', '1080')

    if not any(url.startswith(p) for p in ALLOWED_URL_PREFIXES):
        abort(400, "URL not allowed. Only YouTube URLs are supported.")
    if quality and quality not in ALLOWED_QUALITIES:
        abort(400, "Invalid quality value.")

    session_id = str(uuid.uuid4())
    progress_store[session_id] = {
        "percent": 0,
        "status": "starting",
        "speed": "",
        "eta": "",
        "filepath": None,
        "filename": None,
        "error": None
    }

    download_dir = "/tmp/downloads"
    os.makedirs(download_dir, exist_ok=True)

    if format_type == "mp3":
        fmt = "bestaudio/best"
    elif quality:
        fmt = (
            f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]"
            f"/bestvideo[height<={quality}]+bestaudio"
            f"/best[height<={quality}]"
        )
    else:
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"

    ydl_opts = {
        'format': fmt,
        'quiet': False,
        'no_warnings': False,
        'progress_hooks': [make_progress_hook(session_id)],
        'noplaylist': True,
        'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',

        # ✅ BGUtil POT provider — auto token per video, no cookies needed
        'extractor_args': {
            'youtube': {
                'player_client': ['web'],
                'player_skip': ['webpage'],
            },
            'youtubepot-bgutilhttp': {
                'base_url': ['http://127.0.0.1:4416'],
            },
        },

        # ✅ Retries
        'retries': 15,
        'fragment_retries': 15,
        'extractor_retries': 10,
        'skip_unavailable_fragments': True,

        # ✅ Reconnect on stream drop
        'downloader_options': {
            'ffmpeg_args': [
                '-reconnect', '1',
                '-reconnect_streamed', '1',
                '-reconnect_delay_max', '5'
            ]
        },

        # ✅ Speed
        'concurrent_fragment_downloads': 16,
        'buffersize': 1024 * 16,
        'http_chunk_size': 10485760,

        # ✅ Fast playback start
        'postprocessor_args': {
            'ffmpeg_mergevideo': ['-movflags', 'faststart']
        },
    }

    if format_type == "mp3":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        ydl_opts.pop('merge_output_format', None)
        ydl_opts.pop('postprocessor_args', None)

    def run():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filepath = ydl.prepare_filename(info)
                if format_type == "mp3":
                    filepath = os.path.splitext(filepath)[0] + ".mp3"
                elif not filepath.endswith(".mp4"):
                    filepath = os.path.splitext(filepath)[0] + ".mp4"
                progress_store[session_id]["filepath"] = filepath
                progress_store[session_id]["filename"] = os.path.basename(filepath)
            progress_store[session_id]["percent"] = 100
            progress_store[session_id]["status"] = "done"
        except yt_dlp.utils.DownloadError as e:
            progress_store[session_id]["status"] = "error"
            progress_store[session_id]["error"] = str(e)
        except Exception as e:
            progress_store[session_id]["status"] = "error"
            progress_store[session_id]["error"] = f"Unexpected error: {str(e)}"

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"session_id": session_id})


@app.route('/file/<session_id>')
def serve_file(session_id):
    data = progress_store.get(session_id)
    if not data or data.get("status") != "done":
        abort(404, "File not ready.")
    filepath = data.get("filepath")
    if not filepath or not os.path.exists(filepath):
        abort(404, "File not found on server.")
    return send_file(
        filepath,
        as_attachment=True,
        download_name=data.get("filename", "download")
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)
