from flask import Flask, request, render_template, flash, redirect, Response
from flask_mongoengine import MongoEngine
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
import cv2
from func import image_processing

class VideoCamera(object):

    def __init__(self):
        self.video = cv2.VideoCapture(0)

    def __del__(self):
        self.video.release()

    def get_img(self, param=False):
        ret, frame = self.video.read()

        if param:
            return frame
        else:
            ret, jpeg = cv2.imencode('.jpg', frame)
            return jpeg.tobytes()

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
'db': 'face_detector',
'host': os.environ.get('DB'),
'retryWrites': False
}
app.secret_key = os.environ.get('SECRET_KEY')
db = MongoEngine()
db.init_app(app)
login_manager = LoginManager(app)

@app.after_request
def add_header(response):
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response

@login_manager.user_loader
def load_user(user_id):
    user = User.objects(id=user_id).first()
    return user

class User(db.Document, UserMixin):
    user_name = db.StringField(max_length=128, unique=True, nullable=False)
    _user_pass = db.StringField(max_length=128, nullable=False)
    photo_id = db.ListField(default=[])
    user_date = db.DateTimeField(default=datetime.datetime.now)

    def set_password(self, password):
        self._user_pass = generate_password_hash(password, method='SHA256')

    def check_password(self, password):
        return check_password_hash(self._user_pass, password)


class Photo(db.Document):
    photo_id = db.IntField()
    photo_name = db.StringField()
    count = db.IntField(default=-1)
    done = db.BooleanField(default=False)
    time = db.DateTimeField(default=datetime.datetime.now())

new_id = 0
if Photo.objects().distinct("photo_id"):
    new_id = max(Photo.objects().distinct("photo_id"))+1

@app.route('/image', methods=['GET', 'POST'])
@login_required
def load_img():
    video_stream.__del__()
    if request.method == "POST":
        file = request.files["photo"]
        f_name = file.filename.split('.')
        global new_id
        id = new_id
        new_id += 1
        name = 'p'+str(id)+'.'+f_name[1]
        dir = '/static/'+ name
        file.save(os.getcwd() + dir)
        Photo(photo_id=id, photo_name=name).save()
        User.objects(user_name=current_user.user_name).update_one(push__photo_id=id)
    return render_template("index.html", img_name=name, message="Click on the image", form1='disp', form2='disp')

@app.route('/')
def index():
    return render_template("index.html", form1="disp", form2="disp")

def gen(camera):
    while True:
        pic = camera.get_img()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + pic + b'\r\n\r\n')

@app.route('/video')
def v():
    return render_template("index.html", video =1, form1 = 'disp',form2 = 'disp' )

video_stream = VideoCamera()

@app.route('/get_video')
def get_video():
    global video_stream
    video_stream = VideoCamera()
    return Response(gen(video_stream), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        user = User.objects(user_name = request.form["username"]).first()
        if user and user.check_password(request.form["password"]):
            login_user(user, remember= True)
            return render_template("index.html",form1 = 'disp',form2 = 'disp')
        flash("Invalid username or password")
        return render_template("index.html",form2 = 'disp')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    video_stream.__del__()
    return redirect('/')


@app.route('/registration', methods=['GET', 'POST'])
def reg():
    if request.method == "POST":
        new_user = User.objects(user_name=request.form["username"]).first()
        if new_user == None:
            user = User(user_name=request.form["username"])
            user.set_password(request.form["password"])
            user.save()
            return redirect('/')
        flash("Choose another username please")
        return render_template("index.html", message="NOT_UNIQUE")


@app.route('/count')
@login_required
def face_detector():
    image = request.args.get('image')
    video_stream.__del__()
    if(image == None):
        return 'Image has not been downloaded'
    count = image_processing(image)
    Photo.objects(photo_name=image).first().update(count=count)
    Photo.objects(photo_name=image).first().update(time=datetime.datetime.now())
    name = 'new_'+image
    if count > 1 or count == 0:
        return render_template("index.html",img_name =name , number = str(count), message = "faces found", form1 = 'disp',form2 = 'disp')
    else:
        return render_template("index.html", img_name=name, number = str(count),message="face found", form1 = 'disp',form2 = 'disp')


@app.route('/vcount')
@login_required
def face_detector_v():
    photo = video_stream.get_img(param = True)
    video_stream.__del__()
    global new_id
    id = new_id
    new_id += 1
    name = 'p' + str(id) + '.' + 'jpg'
    dir = '/static/' + name
    cv2.imwrite(os.getcwd() + dir, photo)
    Photo(photo_id=id, photo_name=name).save()
    User.objects(user_name=current_user.user_name).update_one(push__photo_id=id)
    image = name
    if(image == None):
        return 'Image has not been downloaded'
    count = image_processing(image)
    Photo.objects(photo_name=image).first().update(count=count)
    Photo.objects(photo_name=image).first().update(time=datetime.datetime.now())
    name = 'new_'+image

    if count > 1 or count == 0:
        return render_template("index.html", img_name=name, number=str(count), message="faces found", form1='disp', form2='disp')
    else:
        return render_template("index.html", img_name=name, number=str(count), message="face found", form1='disp', form2='disp')


def unauthorized():
    return render_template("index.html", message="Log in first", form1='disp', form2='disp')


login_manager.unauthorized = unauthorized

if __name__ == "__main__":
    app.run()