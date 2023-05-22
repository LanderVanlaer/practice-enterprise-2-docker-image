#!/usr/local/bin/python


# !/usr/bin/python3

# !/usr/bin/python3
import os
import sys
from datetime import datetime

import joblib
import keras
import mariadb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = int(os.getenv("DATABASE_PORT"))
DATABASE_DATABASE = os.getenv("DATABASE_DATABASE")

N_WEEKS_PREDICT = int(os.getenv("N_WEEKS_PREDICT"))

current_dir = os.path.dirname(os.path.abspath(__file__))

model = keras.models.load_model(os.path.join(current_dir, "model.h5"))
window_size = model.layers[0].input_shape[1]

scaler = joblib.load(os.path.join(current_dir, "min-max-scaler.joblib"))

# Connect to MariaDB Platform
try:
    conn = mariadb.connect(
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        database=DATABASE_DATABASE
    )
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

# Get Cursor
cur = conn.cursor()

# noinspection SqlInjection
cur.execute(
    f"SELECT date, ordercount FROM (SELECT date, ordercount FROM ai_order_graph WHERE date < NOW() ORDER BY date DESC LIMIT {window_size}) AS sub ORDER BY date;"
)

df = pd.DataFrame(cur.fetchall())
df.index = pd.to_datetime(df[0])

s = df[1]
s = pd.Series(scaler.transform(s.to_frame()).flatten(), index=s.index)

for _ in range(N_WEEKS_PREDICT):
    X = s[-window_size:]  # Series
    new_index = X.index[-1] + pd.DateOffset(days=7)  # TimeStamp
    value = model.predict(X.values.reshape(-1, window_size))[0][0]

    s = pd.concat([s, pd.Series([value], index=[new_index])], axis=0)

s = pd.Series(scaler.inverse_transform(s.to_frame()).flatten(), index=s.index)

cur.execute("DELETE FROM ai_order_graph WHERE date > NOW()")

temp = s[25:]
val = list(zip([datetime.strptime(str(d)[:10], "%Y-%m-%d").date() for d in temp.index], [int(x) for x in temp.values]))
cur.executemany("INSERT INTO ai_order_graph(date, ordercount) VALUES (%s, %s)", val)

conn.commit()
