import flask
from flask import Blueprint,render_template,request,flash,jsonify
from forex_python.converter import CurrencyRates
from datetime import datetime,timedelta
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense,Dropout,LSTM
from sklearn.preprocessing import MinMaxScaler


currency_rates=CurrencyRates()

forex_predict=Blueprint('forex_predict',__name__)

@forex_predict.route('/forexpredictintro', methods=['POST', 'GET'])
def home():
    if request.method == 'POST':
        base_currency = request.form.get("base_currency", "").strip().upper()
        target_currency = request.form.get("target_currency", "").strip().upper()
        start_date_str = request.form.get("start_date", "").strip()
        end_date_str = request.form.get("end_date", "").strip()

        if not start_date_str or not end_date_str:
            flash("Both dates are required.", "danger")
            return render_template("forexpredictintro.html")

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash("Date format should be YYYY-MM-DD.", "danger")
            return render_template("forexpredictintro.html")

        date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        rates = []

        print("Fetching Data...")
        for date in date_list:
            try:
                rate = currency_rates.get_rate(base_currency, target_currency, date)
                rates.append((date, rate))
            except:
                print(f"Skipping {date.date()} (no data)")
                continue

        if len(rates) <= 60:
            flash("Not enough data to make a prediction. Please choose a longer date range.", "danger")
            return render_template("forexpredictintro.html")


        df = pd.DataFrame(rates, columns=['date', 'Rate'])
        df['days'] = (df['date'] - df['date'].min()).dt.days

        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(df['Rate'].values.reshape(-1, 1))

        prediction_days = 60
        x_train, y_train = [], []

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

        last_60_days = df['Rate'].values[-prediction_days:]
        model_inputs = last_60_days.reshape(-1, 1)
        model_inputs_scaled = scaler.transform(model_inputs)
        x_real = np.reshape(model_inputs_scaled, (1, prediction_days, 1))

        predicted_scaled = model.predict(x_real)
        predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]

        print(f"Predicted Price: {predicted_price}")

        return render_template("forexpredictresult.html", prediction=round(predicted_price, 4), pair=f"{base_currency} to {target_currency}")

    return render_template("forexpredictintro.html")
