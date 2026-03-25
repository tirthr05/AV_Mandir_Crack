from flask import Flask, request, Response, render_template, jsonify
import yt_dlp
import os

app = Flask(__name__)

USERNAME = "admin"
PASSWORD = "admin"

progress_data = {"percent": 0, "status": "idle"}

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

# 🔥 Progress hook
def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%').replace('%', '').strip()
        try:
            progress_data["percent"] = float(percent)
            progress_data["status"] = "downloading"
        except:
            pass
    elif d['status'] == 'finished':
        progress_data["percent"] = 100
        progress_data["status"] = "finished"

@app.route('/progress')
def progress():
    return jsonify(progress_data)

# 🔐 SECRET ROUTE
@app.route('/x9KfL2pQz/download', methods=['POST'])
def download():
    url = request.form['url']
    format_type = request.form['format']
    quality = request.form.get('quality')

    progress_data["percent"] = 0
    progress_data["status"] = "starting"

    # 🎯 Dynamic format selection
    if quality:
        fmt = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}]"
    else:
        fmt = "best"

    ydl_opts = {
        'format': fmt,
        'quiet': True,
        'progress_hooks': [progress_hook],
        'concurrent_fragment_downloads': 10,
        'noplaylist': True
    }

    if format_type == "mp3":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })

    def generate():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        progress_data["status"] = "done"
        yield b"Download complete"

    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
