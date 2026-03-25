from flask import Flask, request, send_file, render_template, Response, jsonify
import yt_dlp
import os

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

USERNAME = "admin"
PASSWORD = "admin"

progress_data = {"percent": 0}

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
        except:
            progress_data["percent"] = 0

@app.route('/progress')
def progress():
    return jsonify(progress_data)

# 🔐 SECRET ROUTE
@app.route('/x9KfL2pQz/download', methods=['POST'])
def download():
    url = request.form['url']
    format_type = request.form['format']
    quality = request.form.get('quality')

    # 🎯 Dynamic resolution (NOT hardcoded exact match)
    if quality:
        fmt = f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}]"
    else:
        fmt = "best"

    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
        'noplaylist': True,
        'concurrent_fragment_downloads': 10,
        'progress_hooks': [progress_hook],
        'quiet': True
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
    else:
        ydl_opts.update({'format': fmt})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if format_type == "mp3":
                filename = os.path.splitext(filename)[0] + ".mp3"

        progress_data["percent"] = 100
        return send_file(filename, as_attachment=True)

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
