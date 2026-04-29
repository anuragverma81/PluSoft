import flask
from werkzeug.security import generate_password_hash,check_password_hash
from flask import Flask,session
from flask import render_template
from flask import request,flash
from flask import redirect,url_for
import sqlite3
from datetime import datetime,timedelta
import json
from flask import Blueprint
from functools import wraps
from .sql import*


auth=Blueprint('auth',__name__)


def init_db():
    conn=sqlite3.connect('site_database.db')
    c=conn.cursor()

    c.execute('''
         CREATE TABLE IF NOT EXISTS site_user(
            
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             username TEXT UNIQUE NOT NULL,
             email TEXT UNIQUE NULL,
             password_hash TEXT NOT NULL          
         ) 
    ''')

    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if "site_user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args,**kwargs)

    return decorated_function

@auth.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        conn = sqlite3.connect('site_database.db')
        c = conn.cursor()

        c.execute('SELECT id FROM site_user WHERE username = ? OR email = ? ', (username, email))
        if c.fetchone():
            flash("username or email already exists")
            return render_template("signup.html")

        password_hash = generate_password_hash(password)

        c.execute('INSERT INTO site_user (username,email,password_hash) VALUES (?,?,?)',
                  (username, email, password_hash))

        conn.commit()
        conn.close()

        flash("Registration successful ! please login.")
        return redirect(url_for('auth.login'))
    return render_template('signup.html')


@auth.route('/login',methods=['POST','GET'])
def login():
   if request.method=='POST':
       username=request.form.get('username')
       password=request.form.get('password')

       conn=sqlite3.connect('site_database.db')
       c=conn.cursor()
       c.execute('SELECT id,password_hash FROM site_user WHERE username=?',(username,))
       site_user=c.fetchone()
       conn.close()

       if site_user and check_password_hash(site_user[1], password):
           session['user_id'] = site_user[0]
           session['username'] = username

           session['site_user_id']=site_user

           return redirect(url_for('views.all'))
       else:
           flash("Invalid username or password")
   return render_template("login.html")


@auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("views.entry_page"))


@login_required
@auth.route('/agent')
def agent():
    return render_template("agent.html")

@login_required
@auth.route('/feedback',methods=['POST','GET'])
def feedback():
    if request.method=='POST':
        name=request.form.get("name")
        email=request.form.get("email")
        feedback=request.form.get("feedback")

        return redirect(url_for("auth.feedback"))


    return render_template("feedback.html")


@login_required
@auth.route('/trading',methods=['POST','GET'])
def trading():
    return render_template("trading.html")
