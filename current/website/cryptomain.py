import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session,Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pycoingecko import CoinGeckoAPI


cryptomain=Blueprint('cryptomain',__name__)

cg = CoinGeckoAPI()
coin_list=cg.get_coins_list()


def init_crypto_db():
    conn = sqlite3.connect('crypto_trading.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT,
                  password_hash TEXT NOT NULL,
                  balance REAL DEFAULT 10000.0,
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

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('cryptomain.login'))
        return f(*args, **kwargs)
    return decorated


def get_coin_id(symbol):
    symbol=symbol.lower()
    for coin in coin_list:
        if coin['symbol']==symbol:
            return coin['id']
    return None

def crypto_data(symbol):
    try:
        coin_id = get_coin_id(symbol.upper())
        if not coin_id:
            return None

        data = cg.get_coin_by_id(coin_id)
        market = data.get('market_data', {})
        current_price = market.get('current_price', {}).get('usd', 0)
        market_cap = market.get('market_cap', {}).get('usd', 0)
        volume = market.get('total_volume', {}).get('usd', 0)
        change_percent = market.get('price_change_percentage_24h', 0)
        change = current_price * (change_percent / 100)
        return {
            'symbol': symbol.upper(),
            'name': data.get('name'),
            'price': round(current_price, 2),
            'market_cap': round(market_cap, 2),
            'volume': round(volume, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2)
        }
    except Exception as e:
        print(f"[ERROR] get_crypto_data: {e}")
        return None

@cryptomain.route('/cryptoindex')
def index():

    return render_template('cryptoindex.html')

@cryptomain.route('/cryptoregister', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('crypto_trading.db')
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
        if c.fetchone():
            flash('Username or email already exists')
            return render_template('cryptoregister.html')
        hash_pw = generate_password_hash(password)
        c.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                  (username, email, hash_pw))
        conn.commit()
        conn.close()
        flash('Registered! Please login.')
        return redirect(url_for('cryptomain.login'))
    return render_template('cryptoregister.html')

@cryptomain.route('/cryptologin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('crypto_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('cryptomain.dashboard'))
        flash('Invalid credentials')
    return render_template('cryptologin.html')

@cryptomain.route('/cryptologout')
def logout():
    session.clear()
    return redirect(url_for('cryptomain.index'))

@cryptomain.route('/cryptodashboard')

def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('cryptomain.login'))

    conn = sqlite3.connect('crypto_trading.db')
    c = conn.cursor()


    c.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],))
    #result = c.fetchone()
    #balance = 1000000
    balance = c.fetchone()[0]


    c.execute('SELECT symbol, shares, avg_price FROM portfolio WHERE user_id = ?', (session['user_id'],))
    portfolio = c.fetchall()
    portfolio_data = []
    portfolio_value = 0
    for symbol, shares, avg_price in portfolio:
        data = crypto_data(symbol)
        if data:
            current_price = data['price']
            value = shares * current_price
            gain_loss = (current_price - avg_price) * shares
            portfolio_data.append({
                'symbol': symbol.upper(),
                'shares': shares,
                'avg_price': avg_price,
                'current_price': current_price,
                'total_value': value,
                'gain_loss': gain_loss
            })
            portfolio_value += value
    c.execute('''SELECT symbol, types, shares, price, timestamp FROM transactions 
                 WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10''', (session['user_id'],))
    transactions = c.fetchall()
    conn.close()
    return render_template('cryptodashboard.html', balance=balance,
                           portfolio=portfolio_data,
                           portfolio_value=portfolio_value,
                           transactions=transactions,

                           )

@cryptomain.route('/cryptotrade', methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session:
        return redirect(url_for('cryptomain.login'))
    if request.method == 'POST':
        symbol = request.form['symbol'].upper()
        action = request.form['action']
        shares = int(request.form['shares'])

        if shares <= 0:
            flash("Shares must be positive.")
            return render_template("cryptotrade.html")

        data = crypto_data(symbol)
        if not data:
            flash("Invalid crypto symbol.")
            return render_template("cryptotrade.html")

        price = data['price']
        total = price * shares

        conn = sqlite3.connect('crypto_trading.db')
        c = conn.cursor()
        c.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],))
        #result = c.fetchone()
        #balance = 1000000
        balance=c.fetchone()[0]


        if action == 'buy':
            if balance < total:
                flash("Not enough funds.")
                conn.close()
                return render_template("cryptotrade.html")
            c.execute('UPDATE users SET balance = ? WHERE id = ?', (balance - total, session['user_id']))
            c.execute('SELECT shares, avg_price FROM portfolio WHERE user_id = ? AND symbol = ?',
                      (session['user_id'], symbol))
            record = c.fetchone()
            if record:
                old_shares, old_avg = record
                new_shares = old_shares + shares
                new_avg = ((old_shares * old_avg) + (shares * price)) / new_shares
                c.execute('UPDATE portfolio SET shares = ?, avg_price = ? WHERE user_id = ? AND symbol = ?',
                          (new_shares, new_avg, session['user_id'], symbol))
            else:
                c.execute('INSERT INTO portfolio (user_id, symbol, shares, avg_price) VALUES (?, ?, ?, ?)',
                          (session['user_id'], symbol, shares, price))
                balance=balance-total

                c.execute('UPDATE users SET balance=? WHERE id=?',(balance-total,session['user_id']))

        elif action == 'sell':
            c.execute('SELECT shares FROM portfolio WHERE user_id = ? AND symbol = ?',
                      (session['user_id'], symbol))
            record = c.fetchone()
            if not record or record[0] < shares:
                flash("Not enough shares.")
                conn.close()
                return render_template("cryptotrade.html")
            remaining = record[0] - shares
            c.execute('UPDATE users SET balance = ? WHERE id = ?', (balance + total, session['user_id']))
            if remaining == 0:
                c.execute('DELETE FROM portfolio WHERE user_id = ? AND symbol = ?',
                          (session['user_id'], symbol))
            else:
                c.execute('UPDATE portfolio SET shares = ? WHERE user_id = ? AND symbol = ?',
                          (remaining, session['user_id'], symbol))

                balance = balance + total

                c.execute('UPDATE users SET balance=? WHERE id=?', (balance + total, session['user_id']))

        c.execute('INSERT INTO transactions (user_id, symbol, types, shares, price) VALUES (?, ?, ?, ?, ?)',
                  (session['user_id'], symbol, action, shares, price))
        conn.commit()
        conn.close()
        flash(f"{action.capitalize()}ed {shares} {symbol} @ ${price:.2f}")
        return redirect(url_for('cryptomain.trade'))

    return render_template('cryptotrade.html')

