from flask import Flask, request, send_file, render_template, Response
import yt_dlp
import os

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔐 PASSWORD PROTECTION
def check_auth(username, password):
    return username == 'admin' and password == 'admin'

@app.before_request
def require_login():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return Response('Login Required', 401,
                        {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/x9KfL2pQz/download', methods=['POST'])  # 🔐 SECRET LINK
def download():
    url = request.form['url']
    format_type = request.form['format']

    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
        'noplaylist': True,
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
        ydl_opts.update({
            'format': 'bestvideo[height<=2160]+bestaudio/best'
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    return send_file(filename, as_attachment=True)

app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
