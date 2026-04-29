import sqlite3
import flask
import requests
import json
from datetime import datetime,timedelta
from flask_login import login_user,logout_user,login_required,current_user
from flask import Flask,render_template,request,redirect,url_for,flash,session,jsonify,Blueprint
from werkzeug.security import generate_password_hash,check_password_hash
from functools import wraps
import yfinance as yf
import threading
import time



stockmain=Blueprint('stockmain',__name__)


def init_db():
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



stock_cache={}
cache_lock=threading.Lock()

def get_stock_data(symbol, retries=3, delay=60):
    for attempt in range(retries):
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1d")

            if hist.empty:
                continue

            current_price = hist['Close'].iloc[-1]
            info = stock.info
            prev_close = info.get("previousClose", current_price)
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close else 0

            return {
                "symbol": symbol,
                "price": round(current_price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": info.get("volume", 0),
                "market_cap": info.get("marketCap", 0),
                "name": info.get("longName", symbol)
            }

        except Exception as e:
            print(f"[{attempt+1}/{retries}] Error fetching data for {symbol}: {e}")
            time.sleep(delay)

    return None



def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if "user_id" not in session:
            return redirect(url_for("stockmain.login"))
        return f(*args,**kwargs)

    return decorated_function

@stockmain.route("/stockhome")
def stock_home():
     return render_template("stockhome.html")

@stockmain.route("/stockregister",methods=['GET','POST'])
def register():
     if request.method=='POST':
        username=request.form.get('username')
        email =request.form.get('email')
        password=request.form.get('password')

        conn=sqlite3.connect('stock_trading.db')
        c=conn.cursor()

        #c.execute('ALTER TABLE users ADD COLUMN email TEXT ')


        c.execute('SELECT id FROM users WHERE username = ? OR email = ? ',(username, email))
        if c.fetchone():
            flash("username or email already exists")
            return render_template("stockregister.html")

        password_hash=generate_password_hash(password)
        c.execute('INSERT INTO users (username,email,password_hash) VALUES (?,?,?)',
                  (username,email,password_hash))

        conn.commit()
        conn.close()

        flash("Registration successful ! please login.")
        return redirect(url_for("stockmain.login"))
     return render_template("stockregister.html")


@stockmain.route('/stocklogin',methods=['GET','POST'])

def login():
    if request.method=='POST':
        username=request.form.get('username').strip()
        password=request.form.get('password').strip()

        conn=sqlite3.connect('stock_trading.db')
        c=conn.cursor()
        c.execute('SELECT id , password_hash FROM users WHERE username = ? ',(username,))
        user=c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('stockmain.trade'))
        else:
            flash("Invalid username or password")
    return render_template("stocklogin.html")


@stockmain.route('/stocklogout')
def logout():
    session.clear()
    return redirect(url_for('stockmain.stock_home'))

@login_required
@stockmain.route('/stockdashboard')
def dashboard():

    user_id=session.get('user_id')
    if user_id is None:
        return redirect(url_for('stockmain.login'))

    conn=sqlite3.connect('stock_trading.db')
    c=conn.cursor()
    c.execute('SELECT balance FROM users WHERE id=?',(user_id,))
    balance=c.fetchone()[0]

    c.execute('''SELECT symbol,shares,avg_price FROM portfolio
                  WHERE user_id=? AND shares>0''',(user_id,))
    portfolio=c.fetchall()
    portfolio_value=0
    portfolio_data=[]
    for symbol,shares,avg_price in portfolio:
        current_data=get_stock_data(symbol)
        if current_data:
            current_price=current_data['price']
            total_value=shares*current_price
            gain_loss=(current_price-avg_price)*shares
            portfolio_value += total_value
            portfolio_data.append({
                'symbol':symbol,
                'shares':shares,
                'avg_price':avg_price,
                'current_price':current_price,
                'total_value':total_value,
                'gain_loss':gain_loss,
            })

    c.execute('''SELECT symbol,types,shares,price,timestamp FROM transactions
                  WHERE user_id=? ORDER BY timestamp DESC LIMIT 10 ''',
              (user_id,))
    transactions=c.fetchall()


    conn.close()
    return render_template("stockdashboard.html",
                           balance=balance,
                           portfolio=portfolio_data,
                           portfolio_value=portfolio_value,
                           transactions=transactions

                           )


@login_required
@stockmain.route('/stocktrade',methods=['GET','POST'])
def trade():
    if request.method=='POST':
        symbol=request.form['symbol'].upper()
        country=request.form['country'].strip().lower()
        action=request.form['action']
        shares=int(request.form['shares'])

        country_suffixes = {
            "united states": "",  # US stocks typically have no suffix
            "usa": "",
            "canada": ".TO",  # Toronto Stock Exchange
            "uk": ".L",  # London Stock Exchange
            "united kingdom": ".L",
            "india": ".NS",  # National Stock Exchange of India (or use ".BO" for BSE)
            "australia": ".AX",  # Australian Securities Exchange
            "germany": ".DE",  # Deutsche Börse
            "france": ".PA",  # Paris Stock Exchange
            "italy": ".MI",  # Milan Stock Exchange
            "spain": ".MC",  # Madrid Stock Exchange
            "switzerland": ".SW",  # SIX Swiss Exchange
            "japan": ".T",  # Tokyo Stock Exchange
            "hong kong": ".HK",  # Hong Kong Stock Exchange
            "south korea": ".KS",  # Korea Stock Exchange (for KOSPI companies)
            "china": ".SS",  # Shanghai Stock Exchange (for Shenzhen, consider ".SZ")
            "brazil": ".SA",  # B3 - Brasil Bolsa Balcão
            "russia": ".ME",  # Moscow Exchange
            "turkey": ".IS",  # Istanbul Stock Exchange
            "israel": ".TA",  # Tel Aviv Stock Exchange
            "singapore": ".SI",  # Singapore Exchange
            "malaysia": ".KL",  # Kuala Lumpur Stock Exchange
            "thailand": ".BK",  # Bangkok Stock Exchange
            "new zealand": ".NZ",  # New Zealand Exchange
            "austria": ".VI",  # Vienna Stock Exchange
            "belgium": ".BR",  # Brussels Stock Exchange
            "denmark": ".CO",  # Copenhagen Stock Exchange
            "finland": ".HE",  # Helsinki Stock Exchange
            "netherlands": ".AS",  # Amsterdam Stock Exchange
            "norway": ".OL",  # Oslo Stock Exchange
            "poland": ".WA",  # Warsaw Stock Exchange (sometimes)
        }

        if country in country_suffixes:
            suffix = country_suffixes.get(country, "")

            if suffix and not symbol.endswith(suffix):
                symbol += suffix


        stock_data=get_stock_data(symbol)
        if not stock_data:
            flash("Invalid Stock Symbol")
            return render_template("stocktrade.html")

        price=stock_data['price']
        total_cost=shares*price

        conn=sqlite3.connect("stock_trading.db")
        c=conn.cursor()

        c.execute('SELECT balance FROM users WHERE id=?',(session['user_id'],))
        balance=c.fetchone()[0]

        if action=='buy':
            if balance<total_cost:
                flash('Insufficient funds')
                conn.close()
                return render_template('stocktrade.html')

            new_balance=balance-total_cost
            c.execute('UPDATE users SET balance=? WHERE id=?',
                      (new_balance,session['user_id']))

            c.execute('SELECT shares,avg_price FROM portfolio WHERE id=? AND symbol=?',(session['user_id'],symbol))
            existing=c.fetchone()

            if existing:
                old_shares,old_avg_price=existing
                new_shares=old_shares+shares
                new_avg_price=((old_shares*old_avg_price)+(shares*price))/new_shares
                c.execute('UPDATE portfolio SET shares=?,avg_price=? WHERE user_id=? AND symbol=?',
                          (new_shares,new_avg_price,session['user_id'],symbol))

            else:
                c.execute('INSERT INTO portfolio (user_id,symbol,shares,avg_price) VALUES(?,?,?,?)',
                          (session['user_id'],symbol,shares,price))

                balance = balance - total_cost

                c.execute('UPDATE users SET balance=? WHERE id=?', (balance - total_cost, session['user_id']))


        elif action=='sell':
            c.execute('SELECT shares FROM portfolio WHERE user_id=? AND symbol=?',
                      (session['user_id'],symbol))
            existing=c.fetchone()

            if not existing or existing[0]<shares:
                flash('Insufficient Shares')
                conn.close()
                return render_template('stocktrade.html')

            new_balance=balance+total_cost
            c.execute('UPDATE users SET balance=? WHERE id=?',
                      (new_balance,session['user_id']))

            new_shares=existing[0]-shares
            if new_shares==0:
                c.execute('DELETE FROM portfolio WHERE user_id=? AND symbol=?',
                          (session['user_id'],symbol))

            else:
                c.execute('UPDATE portfolio SET shares=? WHERE id=? AND symbol=?',
                          (new_shares,session['user_id'],symbol))


                balance = balance + total_cost

                c.execute('UPDATE users SET balance=? WHERE id=?', (balance + total_cost, session['user_id']))


        c.execute('INSERT INTO transactions (user_id,symbol,types,shares,price) VALUES(?,?,?,?,?)',
                  (session['user_id'],symbol,action,shares,price))

        conn.commit()
        conn.close()
        flash(f"successfully {action}ed {shares} shares of {symbol} at ${price:.2f}")
        return redirect(url_for('stockmain.trade'))

    return render_template('stocktrade.html')

@login_required
@stockmain.route('/watchlist',methods=['GET','POST'])
def watchlist():
    conn=sqlite3.connect('stock_trading.db')
    c=conn.cursor()

    c.execute('SELECT symbol FROM watchlist WHERE user_id=?',(session['user_id'],))
    symbols=[row[0] for row in c.fetchall()]
    conn.close()

    watchlist_data=[]
    for symbol in symbols:
        data=get_stock_data(symbol)

        if data:
            watchlist_data.append(data)

    return render_template("stockwatchlist.html",watchlist=watchlist_data)



@login_required
@stockmain.route('/add_to_watchlist',methods=['POST'])
def add_to_watchlist():
    symbol=request.form['symbol'].upper()
    country=request.form['country'].strip().lower()

    country_suffixes = {
        "united states": "",  # US stocks typically have no suffix
        "usa": "",
        "canada": ".TO",  # Toronto Stock Exchange
        "uk": ".L",  # London Stock Exchange
        "united kingdom": ".L",
        "india": ".NS",  # National Stock Exchange of India (or use ".BO" for BSE)
        "australia": ".AX",  # Australian Securities Exchange
        "germany": ".DE",  # Deutsche Börse
        "france": ".PA",  # Paris Stock Exchange
        "italy": ".MI",  # Milan Stock Exchange
        "spain": ".MC",  # Madrid Stock Exchange
        "switzerland": ".SW",  # SIX Swiss Exchange
        "japan": ".T",  # Tokyo Stock Exchange
        "hong kong": ".HK",  # Hong Kong Stock Exchange
        "south korea": ".KS",  # Korea Stock Exchange (for KOSPI companies)
        "china": ".SS",  # Shanghai Stock Exchange (for Shenzhen, consider ".SZ")
        "brazil": ".SA",  # B3 - Brasil Bolsa Balcão
        "russia": ".ME",  # Moscow Exchange
        "turkey": ".IS",  # Istanbul Stock Exchange
        "israel": ".TA",  # Tel Aviv Stock Exchange
        "singapore": ".SI",  # Singapore Exchange
        "malaysia": ".KL",  # Kuala Lumpur Stock Exchange
        "thailand": ".BK",  # Bangkok Stock Exchange
        "new zealand": ".NZ",  # New Zealand Exchange
        "austria": ".VI",  # Vienna Stock Exchange
        "belgium": ".BR",  # Brussels Stock Exchange
        "denmark": ".CO",  # Copenhagen Stock Exchange
        "finland": ".HE",  # Helsinki Stock Exchange
        "netherlands": ".AS",  # Amsterdam Stock Exchange
        "norway": ".OL",  # Oslo Stock Exchange
        "poland": ".WA",  # Warsaw Stock Exchange (sometimes)
    }

    if country in country_suffixes:
        suffix = country_suffixes.get(country, "")

        if suffix and not symbol.endswith(suffix):
            symbol += suffix


    if not get_stock_data(symbol):
        flash('Invalid Stock Symbol')
        return redirect(url_for('stockmain.watchlist'))

    conn=sqlite3.connect('stock_trading.db')
    c=conn.cursor()

    c.execute('SELECT id FROM watchlist WHERE user_id=? AND symbol=?',(session['user_id'],symbol))

    if c.fetchone():
        flash('Stock is  Already in Watchlist')

    else:
        c.execute('INSERT INTO watchlist (user_id,symbol) VALUES(?,?)',
                  (session['user_id'],symbol))
        conn.commit()
        flash(f"Added {symbol} to watchlist")

    conn.close()
    return redirect(url_for('stockmain.watchlist'))

@login_required
@stockmain.route('/remove_from_watchlist/<symbol>')
def remove_from_watchlist(symbol):
    conn=sqlite3.connect('stock_trading.db')
    c=conn.cursor()
    c.execute('DELETE FROM watchlist WHERE user_id=? AND symbol=?',
              (session['user_id'], symbol))

    conn.commit()
    conn.close()

    flash(f'Removed {symbol} successfully')
    return redirect(url_for('stockmain.watchlist',site_user=current_user))


@login_required
@stockmain.route('/api/stock<symbol>')
def api_stock_data(symbol):
    with cache_lock:
        if symbol in stock_cache:
            return jsonify(stock_cache[symbol])

    data=get_stock_data(symbol)
    if data:
        return jsonify(data)
    else:
        return jsonify({'error':'stock not found'})

@login_required
@stockmain.route('/api/portfolio')
def api_portfolio():
    conn=sqlite3.connect('stock_trading.db')
    c=conn.cursor()
    c.execute('SELECT symbol,shares,avg_price FROM portfolio WHERE user_id=? AND shares>0',
              (session['user_id'],))
    portfolio=c.fetchall()
    conn.close()

    portfolio_data=[]
    for symbol,shares,avg_price in portfolio:
        current_data=get_stock_data(symbol)
        if current_data:
            current_price=current_data['price']
            total_value=shares*current_price
            gain_loss=(current_price - avg_price) * shares
            portfolio_data.append({
              'symbol':symbol,
              'avg_price':avg_price,
              'shares':shares,
              'current_price':current_price,
              'total_value':total_value,
              'gain_loss':gain_loss,
              'change_percent':current_data['change_percent']

          })
    return jsonify(portfolio_data)





