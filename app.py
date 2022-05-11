import glob
import io
import os
import shutil
from time import sleep
import cv2
from flask import Flask, Response, redirect, render_template, request, send_file, url_for

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads/'

frames = []
output = None
curr_frame = 0
play = False

class fn:
    def __init__(self, name):
        self.name = name
def getfilepath(loc):
    temp = str(loc).split('\\')
    return temp[-1]


@app.route('/')
def home():
    x = []
    for file in glob.glob("./uploads/*.mp4"):
        res = fn(file)
        x.append(fn(getfilepath(file)))
    return render_template('home.html', results = x)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
        return render_template('process.html', results = (f.filename, 'uploaded'))

@app.route('/load', methods=['GET', 'POST'])
def load():
    if request.method == 'POST':
        filename = request.form['des']
        return render_template('process.html', results = (filename, 'loaded'))

@app.route('/slowmo', methods=['GET', 'POST'])
def process():
    if request.method == 'POST':
        filename = request.values.get('video')
        shutil.copyfile(app.config['UPLOAD_FOLDER']+filename, filename)
        os.system('python slow_movie.py -m '+ filename +' -f 4')
        return render_template('process.html', results = (filename, 'loaded'))

@app.route("/result", methods=['GET', 'POST'])
def result():
    if request.method == 'POST':
        filename = request.form['file']
        file2 = filename[:-4]+'_4x_slow.mp4'
        os.rename(file2, app.config['UPLOAD_FOLDER']+file2)
        return render_template('result.html', result = file2)

@app.route('/download', methods=['GET', 'POST'])
def download():
    if request.method == 'POST':
        filename = request.form['video']
        path = app.config['UPLOAD_FOLDER']+filename
        return send_file(path, as_attachment=True)

@app.route('/edit')
def edit():
    x = []
    for file in glob.glob("./uploads/*.mp4"):
        res = fn(file)
        x.append(fn(getfilepath(file)))
    return render_template('edit.html', results = x)

@app.route('/loadvideo', methods=['GET', 'POST'])
def loadvideo():
    global frames, output, play, curr_frame
    if request.method == 'POST':
        filename = request.form['des']
        path = app.config['UPLOAD_FOLDER']+filename
        cap = cv2.VideoCapture(path)
        size = (int(cap.get(3)), int(cap.get(4)))
        output = cv2.VideoWriter(path[:-4]+'.avi', cv2.VideoWriter_fourcc(*'MJPG'), 24, size)
        frames = []
        play = False
        curr_frame = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()
        cv2.destroyAllWindows()
        return redirect(url_for('display'))

@app.route('/display')
def display():
    return render_template('editor.html')

def gen():
    global curr_frame
    while True:
        _, image_buffer = cv2.imencode('.jpg', frames[curr_frame])
        if play:
            curr_frame = (curr_frame+1)%len(frames)
        sleep(1/24)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')

@app.route('/editvideo')
def editvideo():
    return Response(
        gen(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/play')
def play():
    global play
    play = not play
    return redirect(url_for('display'))

@app.route('/prev')
def prev():
    global curr_frame, frames
    curr_frame = (curr_frame-1)%len(frames)
    return redirect(url_for('display'))

@app.route('/next')
def next():
    global curr_frame, frames
    curr_frame = (curr_frame+1)%len(frames)
    return redirect(url_for('display'))

@app.route('/delete')
def delete():
    global curr_frame, frames
    frames = frames[:curr_frame]+frames[curr_frame+1:]
    curr_frame = curr_frame%len(frames)
    return redirect(url_for('display'))

@app.route('/frame', methods=['GET', 'POST'])
def frame():
    global curr_frame, frames
    if request.method == 'POST':
        num = int(request.values.get('number'))
        if 0<=num<len(frames):
            curr_frame = num
        return redirect(url_for('display'))

@app.route('/savevideo')
def savevideo():
    global frames, output
    for frame in frames:
        output.write(frame)
    output.release()
    frames = []
    return redirect(url_for('edit'))

if __name__ == '__main__':
    app.run()