import flask
from flask import Blueprint,render_template,request,flash,jsonify
from flask_login import login_required
from pycoingecko import CoinGeckoAPI
import numpy as np
import pandas as pd
import datetime as dt
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense,Dropout,LSTM
import time
from requests.exceptions import HTTPError

from .sql import*

cg = CoinGeckoAPI()

crypto_predict=Blueprint('crypto_predict',__name__)

@login_required
@crypto_predict.route('/intro',methods=['POST','GET'])
def home():
     if request.method=='POST':
         coin = request.form.get("coin","").strip().lower()
         vs_currency = request.form.get("vs_currency","").strip().lower()
         start_str = request.form.get("start_date","").strip()
         end_str = request.form.get("end_date","").strip()

         if not coin or not vs_currency or not start_str or not end_str:
             flash("All field are required.", category='error')
             return render_template("intro.html")

         try:
             start_dt = dt.datetime.strptime(start_str, "%Y-%m-%d")
             end_dt = dt.datetime.strptime(end_str, "%Y-%m-%d")
             start_ts = int(start_dt.timestamp())
             end_ts = int(end_dt.timestamp())
             hist = cg.get_coin_market_chart_range_by_id(
                 id=coin,
                 vs_currency=vs_currency,
                 from_timestamp=start_ts,
                 to_timestamp=end_ts
             )

         except HTTPError as e:
             flash(f"Error fetching data :{e}", category='error')
             return render_template("intro.html")
         except ValueError:
             flash("Invalid date format. Use YYYY-MM-DD.", category='error')
             return render_template("intro.html")

         df = pd.DataFrame(hist['prices'], columns=['timestamp_ms', 'Close'])
         df['Date'] = pd.to_datetime(df['timestamp_ms'], unit='ms')
         df.set_index('Date', inplace=True)
         df = df[['Close']]

         scaler = MinMaxScaler(feature_range=(0, 1))
         scaled_data = scaler.fit_transform(df['Close'].values.reshape(-1, 1))

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
         model.fit(x_train, y_train, epochs=25, batch_size=32, verbose=0)

         last_60_days = df['Close'].values[-prediction_days:]
         model_inputs = last_60_days.reshape(-1, 1)

         x_real = model_inputs.reshape((1, prediction_days, 1))
         predicted_scaled = model.predict(x_real)
         predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]

         return render_template("output.html", prediction=round(predicted_price, 2), coin=coin.upper(),
                                currency=vs_currency.upper())

     return render_template("intro.html")