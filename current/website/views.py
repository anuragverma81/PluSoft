from flask import Blueprint,render_template,request,flash,jsonify
from flask_login import login_required
import numpy as np
import pandas as pd
import datetime as dt
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense,Dropout,LSTM
import time

#from .import db
import json

from .sql import*

views=Blueprint('views',__name__)

@views.route('/',methods=['POST','GET'])
def entry_page():
    return render_template('entry.html')

@login_required
@views.route('/all',methods=['POST','GET'])
def all():
    return render_template("all.html")



@login_required
@views.route('/home',methods=['POST','GET'])
def home():

    prediction=None
    if request.method=='POST':
        company=request.form["company"]
        country=request.form.get("country","").strip().lower()
        start_str=request.form["start_date"]
        end_str=request.form["end_date"]

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
            suffix=country_suffixes.get(country,"")

            if suffix and not company.endswith(suffix):
                company+=suffix

        try:
            start = dt.datetime.strptime(start_str, "%Y-%m-%d")
            end = dt.datetime.strptime(end_str, "%Y-%m-%d")

        except ValueError:
            return render_template("home.html",error="Invalid date format.Please use YYYY-MM-DD")



        def safe_download(ticker, start, end, retries=3, delay=60, _ERRORS=None):
            for attempt in range(retries):
                try:
                    data = yf.download(ticker, start=start, end=end, progress=False, threads=False)
                    if not data.empty:
                        return data
                except _ERRORS.YFRateLimitError:
                    print(f"Rate limit hit. Waiting {delay} seconds...")
                    time.sleep(delay)
                except Exception as e:
                    print(f"Error: {e}")
                    break
            return None

        data = safe_download(company, start, end)

        if data is None:
            flash("Failed to fetch pls try again later","danger")
            return render_template("home.html",error="Insuffient data")

        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1, 1))

        prediction_days = 60

        x_train = []
        y_train = []

        for x in range(prediction_days, len(scaled_data)):
            x_train.append(scaled_data[x - prediction_days:x, 0])
            y_train.append(scaled_data[x, 0])
        x_train, y_train = np.array(x_train), np.array(y_train)
        x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
        model = Sequential()
        model.add(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
        model.add(Dropout(0.2))
        model.add(LSTM(units=50, return_sequences=True))
        model.add(Dropout(0.2))
        model.add(LSTM(units=50))
        model.add(Dropout(0.2))
        model.add(Dense(units=1))
        model.compile(optimizer='adam', loss='mean_squared_error')
        model.fit(x_train, y_train, epochs=25, batch_size=32,verbose=0)
        last_60_days=data['Close'].values[-prediction_days:]
        model_inputs=last_60_days.reshape(-1,1)
        model_inputs=scaler.transform(model_inputs)
        x_real=[]
        x_real.append(model_inputs[:,0])
        x_real=np.array(x_real)
        x_real=np.reshape(x_real,(x_real.shape[0],x_real.shape[1],1))
        predicted_price=model.predict(x_real)
        predicted_price=scaler.inverse_transform(predicted_price)
        prediction=round(predicted_price[0][0],2)

        return render_template("result.html",company=company,prediction=prediction)


    return render_template("home.html")



