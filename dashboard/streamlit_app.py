"""
IoT Lab2 Dashboard - Streamlit
Hiển thị dữ liệu real-time và processed từ InfluxDB.
"""
import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

load_dotenv()

client = InfluxDBClient(
    url=os.getenv("INFLUX_URL"),
    token=os.getenv("INFLUX_TOKEN"),
    org=os.getenv("INFLUX_ORG"),
)
query_api = client.query_api()
bucket = os.getenv("INFLUX_BUCKET", "iot_data")

st.set_page_config(page_title="IoT Lab2 Dashboard", layout="wide")
st.title("📊 IoT Lab2 - Real-time Dashboard")

# --- Panel 1: Raw data ---
st.subheader("1. Dữ liệu thô (Raw) - 15 phút gần nhất")
q_raw = f'''
from(bucket: "{bucket}")
  |> range(start: -15m)
  |> filter(fn: (r) => r._measurement == "sensor_raw")
  |> filter(fn: (r) => r._field == "temperature" or r._field == "humidity" or r._field == "light")
  |> aggregateWindow(every: 5s, fn: mean, createEmpty: false)
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''
df_raw = query_api.query_data_frame(q_raw)
if isinstance(df_raw, list):
    df_raw = pd.concat(df_raw, ignore_index=True) if df_raw else pd.DataFrame()
if not df_raw.empty:
    df_raw = df_raw[["_time", "temperature", "humidity", "light"]].set_index("_time")
    st.line_chart(df_raw)
else:
    st.info("Chưa có dữ liệu raw. Hãy chạy simulator + collector.")

# --- Panel 2: Latency ---
st.subheader("2. End-to-End Latency")
q_lat = f'''
from(bucket: "{bucket}")
  |> range(start: -15m)
  |> filter(fn: (r) => r._measurement == "latency")
  |> filter(fn: (r) => r._field == "end_to_end_ms")
'''
df_lat = query_api.query_data_frame(q_lat)
if isinstance(df_lat, list):
    df_lat = pd.concat(df_lat, ignore_index=True) if df_lat else pd.DataFrame()
if not df_lat.empty:
    st.line_chart(df_lat[["_time", "_value"]].set_index("_time"))
    col1, col2, col3 = st.columns(3)
    col1.metric("Mean (ms)", f"{df_lat['_value'].mean():.2f}")
    col2.metric("Min (ms)", f"{df_lat['_value'].min():.2f}")
    col3.metric("Max (ms)", f"{df_lat['_value'].max():.2f}")
else:
    st.info("Chưa có dữ liệu latency.")

# --- Panel 3: Processed ---
st.subheader("3. Dữ liệu đã tiền xử lý (Processed)")
q_proc = f'''
from(bucket: "{bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "sensor_processed")
  |> filter(fn: (r) => r._field == "temperature" or r._field == "temp_roll_mean_5")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''
df_proc = query_api.query_data_frame(q_proc)
if isinstance(df_proc, list):
    df_proc = pd.concat(df_proc, ignore_index=True) if df_proc else pd.DataFrame()
if not df_proc.empty:
    st.line_chart(df_proc.set_index("_time")[["temperature", "temp_roll_mean_5"]])
else:
    st.info("Chưa có dữ liệu processed. Hãy chạy preprocess.py.")