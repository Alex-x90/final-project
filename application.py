import os
import requests, json

from json import loads
from flask import Flask, session, render_template, jsonify, redirect, request,url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

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

@app.route("/" , methods=["GET","POST"])
def index():
    posts = db.execute("select * from posts order by id desc")
    return render_template("main.html",account=session["account"],posts=posts)

@app.route("/create_post" , methods=["GET","POST"])
def new():


@app.route("/post/<int:post_id>" , methods=["GET","POST"])
def post(post_id):
    post = db.execute("select * from posts where id = :id",{"id":post_id})
    return render_template("post.html",account=session["account"],post=post)

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

@app.route("/logout")
def logout():
    #logs the user out by deleting informtion from the session that stores their information
    session["account"] = None
    return render_template("login.html")

@app.route("/login" , methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    if request.method == 'POST':

        username = request.form.get("username")
        password = request.form.get("password")

        #checks if the users username and password match up with a username and password pair in the database.
        if db.execute("SELECT * FROM accounts WHERE username = :username and password = :password", {"username": username,"password": password }).rowcount == 0:
            if db.execute("SELECT * FROM accounts WHERE username = :username ", {"username": username}).rowcount == 0:
                return render_template("error.html", message="That account doesn't exist")
            return render_template("error.html", message="You entered the incorrect password")
        else:

            #sets up the account session if there isn't one so that if the user logs in the website can store their username and display it.
            if session.get("account") is None:
                session["account"] = []
            data_request = 1
            session["account"] = username
            return render_template("main.html", account = session["account"])