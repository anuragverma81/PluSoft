import sqlite3
from flask_login import UserMixin


def init_db():
    conn=sqlite3.connect('site_database.db')
    c=conn.cursor()

    c.execute('''
            CREATE TABLE IF NOT EXISTS site_user(

                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NULL,
                username TEXT UNIQUE NOT NULL,
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
    def get(user_id):
        conn = sqlite3.connect('stock_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, email,name FROM user WHERE id=?', (user_id,))

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
    def __init__(self, id, email, name):
        self.id = str(id)
        self.email = email
        self.name = name

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect('forex_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, email,name FROM site_user WHERE id=?', (user_id,))

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
    def __init__(self, id, email, name, balance):
        self.id = str(id)
        self.email = email
        self.name = name
        self.balance = balance

    @staticmethod
    def get(user_id, email):
        conn = sqlite3.connect('forex_trading.db')
        c = conn.cursor()
        c.execute('SELECT id, email,name FROM forex_users WHERE id=? ', (user_id,))

        row = c.fetchone()
        conn.close()

        if row:
            return CryptoUser(*row)
        return None


