from functools import wraps

from flask import Flask, redirect, url_for, session
import threading
import sqlite3
from os import path
from flask_login import LoginManager, UserMixin
import os
from flask_socketio import SocketIO
from extensions import socketio
from .sql import*

import threading

def init_db():
    conn = sqlite3.connect('site_database.db')
    c = conn.cursor()

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


class SiteUser(UserMixin):
    def __init__(self, id, email, name):
        self.id = str(id)
        self.email = email
        self.name = name

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect('site_databse.db')
        c = conn.cursor()
        c.execute('SELECT id, email,name FROM site_user WHERE id=?', (user_id,))

        row = c.fetchone()
        conn.close()

        if row:
            return SiteUser(*row)
        return None

def init_stock_db():
    conn=sqlite3.connect('stock_trading.db')
    c=conn.cursor()


    c.execute('''CREATE TABLE IF NOT  EXISTS users
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  balance REAL DEFAULT 100000.00,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''
              )

    c.execute('''CREATE TABLE IF NOT EXISTS portfolio
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  symbol TEXT NOT NULL,
                  shares INTEGER NOT NULL,
                  avg_price REAL NOT NULL,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     symbol TEXT NOT NULL,
                     user_id INTEGER,
                     types TEXT NOT NULL,
                     shares INTEGER NOT NULL,
                     price  REAL NOT NULL,
                     timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY(user_id) REFERENCES users (id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS watchlist
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()


class User(UserMixin):
    def __init__(self, id, email, name,balance):
        self.id = str(id)
        self.email = email
        self.name = name
        self.balance=balance

    @staticmethod
    def get(user_id,email):
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, email,name FROM user WHERE id=? ', (user_id,))

        row = c.fetchone()
        conn.close()

        if row:
            return User(*row)
        return None

def init_forex_db():
    conn = sqlite3.connect('forex_trading.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    balance REAL DEFAULT 10000.0
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    base_currency TEXT NOT NULL,
                    target_currency TEXT NOT NULL,
                    amount REAL NOT NULL,
                    rate REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')

    conn.commit()
    conn.close()


class ForexUser(UserMixin):
    def __init__(self, id, email, name,balance):
        self.id = str(id)
        self.email = email
        self.name = name
        self.balance=balance

    @staticmethod
    def get(user_id,email):
        conn = sqlite3.connect('forex_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, email,name FROM forex_users WHERE id=? ', (user_id,))

        row = c.fetchone()
        conn.close()

        if row:
            return ForexUser(*row)
        return None


def init_crypto_db():
    conn = sqlite3.connect('crypto_trading.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT,
                  password_hash TEXT NOT NULL,
                  balance REAL DEFAULT 100000.00,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  symbol TEXT NOT NULL,
                  shares INTEGER NOT NULL,
                  avg_price REAL NOT NULL,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  symbol TEXT NOT NULL,
                  user_id INTEGER,
                  types TEXT NOT NULL,
                  shares INTEGER NOT NULL,
                  price REAL NOT NULL,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users (id))''')
    conn.commit()
    conn.close()


class CryptoUser(UserMixin):
    def __init__(self, id, email, name,balance):
        self.id = str(id)
        self.email = email
        self.name = name
        self.balance=balance

    @staticmethod
    def get(user_id,email):
        conn = sqlite3.connect('forex_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, email,name FROM forex_users WHERE id=? ', (user_id,))

        row = c.fetchone()
        conn.close()

        if row:
            return CryptoUser(*row)
        return None




def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "site_user_id" not in session:
                return redirect(url_for("auth.login"))
            return f(*args, **kwargs)

        return decorated_function



def create_app():
    app=Flask(__name__)
    app.config['SECRET_KEY']="HYGHHEWFFJ"
    init_db()
    init_stock_db()
    init_forex_db()
    init_crypto_db()

    from .views import views
    from .auth import auth
    from .server import server
    from .application import application
    from .crypto_predict import crypto_predict
    from .pschyo import pschyo
    from .stockmain import stockmain
    from .forexmain import forexmain
    from .cryptomain import cryptomain
    from.forex_predict import forex_predict

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(pschyo, url_prefix='/')
    app.register_blueprint(server, url_prefix='/')
    app.register_blueprint(application, url_prefix='/')
    app.register_blueprint(crypto_predict, url_prefix='/')
    app.register_blueprint(stockmain, url_prefix='/')
    app.register_blueprint(forexmain,url_prefix='/')
    app.register_blueprint(cryptomain,url_prefix='/')
    app.register_blueprint(forex_predict,url_prefix='/')

    socketio = SocketIO(async_mode='threading')

    socketio.init_app(app)

    login_manager=LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return SiteUser
    return app

