from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_mail import Mail
import json
import os
import pymysql
import math
pymysql.install_as_MySQLdb()

local_server = True
with open('config.json', 'r') as c:
    parameters = json.load(c)["parameters"]

app = Flask(__name__)
app.secret_key = 'the_random_string'
app.config['UPLOAD_FOLDER'] = parameters['uploader_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=parameters['gmail_user'],
    MAIL_PASSWORD=parameters['gmail_password']
)
mail = Mail(app)
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = parameters['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = parameters['prod_uri']
db = SQLAlchemy(app)


class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    mess = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(30), nullable=False)
    content = db.Column(db.String(12), nullable=False)
    tagline = db.Column(db.String(12), nullable=False)
    date = db.Column(db.String(12), nullable=True)


@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(parameters['no_of_posts']))
    #[0:parameters['no_of_posts']]
    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(parameters['no_of_posts']): (page-1)*int(parameters['no_of_posts'])+int(parameters['no_of_posts'])]
    #pagination logic
    if page==1:
      prev = "#"
      next = "/?page="+ str(page+1)
    elif page==last:
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template('index.html', parameters=parameters, posts=posts, prev=prev, next=next)


@app.route("/about")
def about():
    return render_template('about.html', parameters=parameters)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == parameters['admin_user']:
        posts = Posts.query.all()
        return render_template('dashboard.html', parameters=parameters, posts=posts)
    if request.method == 'POST':
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if username == parameters['admin_user'] and userpass == parameters['admin_password']:
            # set the session variable
            session['user'] = username
            posts = Posts.query.all()
        return render_template('dashboard.html', parameters=parameters, posts=posts)
    else:
        return render_template('login.html', parameters=parameters)


@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()

    return render_template('post.html', parameters=parameters, post=post)


@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if 'user' in session and session['user'] == parameters['admin_user']:
        if request.method == 'POST':
            title = request.form.get('title')
            tagline = request.form.get('tagline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            date = datetime.now()
            if sno == '0':
                post = Posts(title=title, tagline=tagline, slug=slug, content=content, date=date)
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = title
                post.tagline = tagline
                post.slug = slug
                post.content = content
                post.date = date
                db.session.commit()
                return redirect('/edit' + sno)
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', parameters=parameters, post=post)


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if 'user' in session and session['user'] == parameters['admin_user']:
        if request.method == 'POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded Successfully"


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')


@app.route("/delete/<string:sno>", methods=['GET', 'POST'])
def delete(sno):
    if 'user' in session and session['user'] == parameters['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, email=email, phone=phone, mess=message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New message from ' + name,
                          sender=email,
                          recipients=[parameters['gmail_user']],
                          body=message + "\n" + phone
                          )
    return render_template('contact.html', parameters=parameters)


app.run(debug=True)
