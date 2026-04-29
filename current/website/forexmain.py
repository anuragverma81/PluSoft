
from flask import Flask, render_template, request, redirect, url_for, flash, session,Blueprint
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from datetime import datetime


forexmain=Blueprint('forexmain',__name__)




def init_db():
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


def get_exchange_rate(base_currency, target_currency):
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={base_currency}&vs_currencies={target_currency}'
    response = requests.get(url)
    data = response.json()
    try:
        rate = data[base_currency][target_currency]
        return rate
    except KeyError:
        return None

@forexmain.route('/forexhome')
def index():
    return render_template('forexhome.html')

@forexmain.route('/forexregister', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        conn = sqlite3.connect('forex_trading.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
            conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('forexmain.login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.')
            return redirect(url_for('forexmain.register'))
        finally:
            conn.close()
    return render_template('forexregister.html')

@forexmain.route('/forexlogin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('forex_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('forexmain.dashboard'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('forexmain.login'))
    return render_template('forexlogin.html')

@forexmain.route('/forexlogout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('forexmain.index'))

@forexmain.route('/forexdashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('forexmain.login'))
    conn = sqlite3.connect('forex_trading.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],))
    balance = c.fetchone()[0]
    c.execute('SELECT base_currency, target_currency, amount, rate, timestamp FROM trades WHERE user_id = ?', (session['user_id'],))
    trades = c.fetchall()
    conn.close()
    return render_template('forexdashboard.html', balance=balance, trades=trades)

@forexmain.route('/trade', methods=['GET', 'POST'])
def trade():
    if 'user_id' not in session:
        return redirect(url_for('forexlogin'))
    if request.method == 'POST':
        base_currency = request.form['base_currency'].lower()
        target_currency = request.form['target_currency'].lower()
        amount = float(request.form['amount'])
        rate = get_exchange_rate(base_currency, target_currency)
        if rate is None:
            flash('Invalid currency pair.')
            return redirect(url_for('forexmain.trade'))
        total_cost = amount * rate
        conn = sqlite3.connect('forex_trading.db')
        c = conn.cursor()
        c.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],))
        balance = c.fetchone()[0]
        if balance < total_cost:
            flash('Insufficient balance.')
            conn.close()
            return redirect(url_for('forexmain.trade'))
        new_balance = balance - total_cost
        c.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, session['user_id']))
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO trades (user_id, base_currency, target_currency, amount, rate, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (session['user_id'], base_currency, target_currency, amount, rate, timestamp))
        conn.commit()
        conn.close()
        flash(f'Trade executed: Bought {amount} {base_currency.upper()} at rate {rate} {target_currency.upper()}')
        return redirect(url_for('forexmain.dashboard'))
    return render_template('forextrade.html')




