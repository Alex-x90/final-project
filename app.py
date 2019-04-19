import os
import requests, json
from datetime import datetime,timezone,timedelta

from json import loads
from flask import Flask, session, render_template, jsonify, redirect, request,url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import re
import lxml.html

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def replace_url_to_link(value):
    # Replace url to link
    urls = re.compile(r"((https?):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.MULTILINE|re.UNICODE)
    value = urls.sub(r'<a href="\1" target="_blank">\1</a>', value)
    # Replace email to mailto
    urls = re.compile(r"([\w\-\.]+@(\w[\w\-]+\.)+[\w\-]+)", re.MULTILINE|re.UNICODE)
    value = urls.sub(r'<a href="mailto:\1">\1</a>', value)
    return value

@app.route("/")
def index():
    if session.get("account") is None:
        account = None
    else:
        account = session["account"]
    posts = db.execute("select * from posts where response_to is null order by id desc")
    return render_template("main.html",account=account,posts=posts)

@app.route("/edit/<post_id>", methods=["GET","POST"])
def edit(post_id):
    if request.method == 'GET':
        if session.get("account") is None:
            return render_template("error.html", message="You must be logged in to edit a post.")
        account = str(db.execute("select username from posts where id =:id",{"id":post_id}).fetchone())
        account = account[:-3]
        account = account[2:]
        if(account != session.get("account")):
            return render_template("error.html", message="You cannot edit someone else's post!")
        reply = str(db.execute("select response_to from posts where id =:id",{"id":post_id}).fetchone())
        current_text=str(db.execute("select post from posts where id =:id",{"id":post_id}).fetchone())
        current_text = current_text[:-3]
        current_text = current_text[2:]
        current_text = lxml.html.fromstring(current_text).text_content()
        if reply == "(None,)":
            current_title = str(db.execute("select title from posts where id =:id",{"id":post_id}).fetchone())
            current_title = current_title[:-3]
            current_title = current_title[2:]
            return render_template("new_post.html",account=session["account"],edit=True,post_id=post_id,reply=False,current_text=current_text,current_title=current_title)
        return render_template("new_post.html",account=session["account"],edit=True,post_id=post_id,reply=True,current_text=current_text)
    if request.method == 'POST':
        reply = str(db.execute("select response_to from posts where id =:id",{"id":post_id}).fetchone())
        content = request.form.get("text")
        content = lxml.html.fromstring(content).text_content()
        content = replace_url_to_link(content)
        if reply != "(None,)":
            reply = reply[:-2]
            reply = reply[1:]
            db.execute("update posts set post = :post where id=:id",{"post":content,"id":post_id})
            db.commit()
            return redirect ('/post/'+reply)
        title = request.form.get("title")
        db.execute("update posts set title = :title where id=:id",{"id":post_id,"title":title})
        db.execute("update posts set post = :post where id=:id",{"post":content,"id":post_id})
        db.commit()
        return redirect( url_for('index'))


@app.route("/delete/<post_id>", methods=["POST"])
def delete(post_id):
    account = str(db.execute("select username from posts where id =:id",{"id":post_id}).fetchone())
    account = account[:-3]
    account = account[2:]
    if(account != session.get("account")):
        return render_template("error.html", message="You cannot delete someone else's post!")
    reply = str(db.execute("select response_to from posts where id =:id",{"id":post_id}).fetchone())
    db.execute("delete from posts where id = :id",{"id":post_id})
    db.execute("delete from posts where response_to=:id",{"id":post_id})
    db.commit()
    if reply != "(None,)":
        reply = reply[:-2]
        reply = reply[1:]
        return redirect ('/post/'+reply)
    return redirect( url_for('index'))

@app.route("/create_post" , methods=["GET","POST"])
def new():
    if request.method == 'GET':
        if session.get("account") is None:
            return render_template("error.html", message="You must be logged in to create a new post.")
        return render_template("new_post.html",account=session["account"])
    if request.method == 'POST':
        title = request.form.get("title")
        content = request.form.get("text")
        content = lxml.html.fromstring(content).text_content()
        content = replace_url_to_link(content)
        username = session["account"]
        time = datetime.now(timezone(-timedelta(hours=4),"EST" )).strftime('%Y-%m-%d %H:%M:%S %Z')
        db.execute("insert into posts (title,post,username,time) values (:title,:post,:username,:time)",{"title":title,"post":content,"username":username,"time":time})
        db.commit()
        post_id = str(db.execute("select id from posts where title = :title and post = :post and username = :username",{"title":title,"post":content,"username":username}).fetchone())
        post_id = post_id[:-2]
        post_id = post_id[1:]
        return redirect( url_for('post',post_id=post_id))

@app.route("/reply/<post_id>", methods=["GET","POST"])
def reply(post_id):
    if request.method == 'GET':
        if session.get("account") is None:
            return render_template("error.html", message="You must be logged in to reply to a post.")
        return render_template("new_post.html",account=session["account"],reply=True,post_id=post_id)
    if request.method == 'POST':
        content = request.form.get("text")
        content = lxml.html.fromstring(content).text_content()
        content = replace_url_to_link(content)
        username = session["account"]
        time = datetime.now(timezone(-timedelta(hours=4),"EST" )).strftime('%Y-%m-%d %H:%M:%S %Z')
        db.execute("insert into posts (post,username,time,response_to) values (:post,:username,:time,:response_to)",{"post":content,"username":username,"response_to":post_id,"time":time})
        db.commit()
        return redirect( url_for('post',post_id=post_id))

@app.route("/post/<post_id>" , methods=["GET","POST"])
def post(post_id):
    if session.get("account") is None:
        account = None
    else:
        account = session["account"]
    reply = str(db.execute("select response_to from posts where id =:id",{"id":post_id}).fetchone())
    if reply != "(None,)":
        post_id = reply[:-2]
        post_id = post_id[1:]
    posts = db.execute("select * from posts where id = :id",{"id":post_id})
    replies = db.execute("select * from posts where response_to = :id order by id desc",{"id":post_id})
    return render_template("post.html",account=account,posts=posts,replies=replies,post_id=post_id)





@app.route("/register" , methods=["GET","POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        #gets username and password from form.

        #checks if that username is already in the database. if results are none it means it isnt and it tries to store the username and password entered. otherwise it gives an error.
        if db.execute("SELECT * FROM accounts WHERE username = :username", {"username": username}).rowcount != 0:
            return render_template("error.html", message="That username already exists")
        db.execute("INSERT INTO accounts (username, password) VALUES (:username,:password)",{"username":username,"password":password})
        db.commit()
        return render_template("login.html")

@app.route("/logout/<post_id>", methods=["GET","POST"])
def logout(post_id):
    #logs the user out by deleting informtion from the session that stores their information
    session["account"] = None
    post_id=int(post_id)
    if post_id<0:
        return redirect( url_for('index'))
    else:
        return redirect( url_for('post',post_id=post_id))

@app.route("/login" , methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    if request.method == 'POST':

        username = request.form.get("username")
        password = request.form.get("password")

        #checks if the users username and password match up with a username and password pair in the database.
        if db.execute("SELECT * FROM accounts WHERE username = :username and password = :password", {"username": username,"password": password }).rowcount == 0:
            return render_template("error.html", message="If that account exists your credentials were incorrect.")
        else:
            if session.get("account") is None:
                session["account"] = []
            session["account"] = username
            return redirect( url_for('index'))
