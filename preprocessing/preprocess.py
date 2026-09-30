"""
Tiền xử lý dữ liệu IoT:
- Đọc dữ liệu raw từ InfluxDB
- Xử lý missing values
- Phát hiện & thay thế outlier bằng IQR
- Resample theo cửa sổ 1 phút
- Tạo feature: rolling mean, delta
- Chuẩn hóa MinMax
- Ghi kết quả vào measurement 'sensor_processed'
"""
import os
import warnings

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")
load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()
write_api = client.write_api(write_options=SYNCHRONOUS)


def fetch_raw(minutes: int = 30) -> pd.DataFrame:
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{minutes}m)
      |> filter(fn: (r) => r._measurement == "sensor_raw")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    df = query_api.query_data_frame(query)
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True) if df else pd.DataFrame()
    if df.empty:
        return df
    df = df.rename(columns={"_time": "timestamp"})
    cols = ["timestamp", "device_id", "temperature", "humidity", "light"]
    df = df[[c for c in cols if c in df.columns]]
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("UTC")
    return df


def fill_missing(g: pd.DataFrame) -> pd.DataFrame:
    g = g.set_index("timestamp").sort_index()
    g = g[["temperature", "humidity", "light"]]
    g = g.interpolate(method="time").ffill().bfill()
    return g


def replace_outliers_iqr(g: pd.DataFrame, cols) -> pd.DataFrame:
    for col in cols:
        q1 = g[col].quantile(0.25)
        q3 = g[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        g[col] = np.where((g[col] < lower) | (g[col] > upper), np.nan, g[col])
    return g.interpolate(method="time").ffill().bfill()


def add_features(g: pd.DataFrame) -> pd.DataFrame:
    g["temp_roll_mean_5"] = g["temperature"].rolling(5, min_periods=1).mean()
    g["hum_roll_mean_5"] = g["humidity"].rolling(5, min_periods=1).mean()
    g["temp_delta"] = g["temperature"].diff().fillna(0)
    return g


def normalize(g: pd.DataFrame) -> pd.DataFrame:
    scaler = MinMaxScaler()
    g[["temperature_norm", "humidity_norm"]] = scaler.fit_transform(
        g[["temperature", "humidity"]]
    )
    return g


def process_device(g: pd.DataFrame) -> pd.DataFrame:
    g = fill_missing(g)
    g = replace_outliers_iqr(g, ["temperature", "humidity", "light"])
    g = g.resample("1min").mean()
    g = add_features(g)
    g = normalize(g)
    return g


def write_processed(device_id: str, df: pd.DataFrame):
    for ts, row in df.iterrows():
        if pd.isna(row["temperature"]):
            continue
        point = (
            Point("sensor_processed")
            .tag("device_id", device_id)
            .field("temperature", float(row["temperature"]))
            .field("humidity", float(row["humidity"]))
            .field("light", float(row["light"]))
            .field("temp_roll_mean_5", float(row["temp_roll_mean_5"]))
            .field("hum_roll_mean_5", float(row["hum_roll_mean_5"]))
            .field("temp_delta", float(row["temp_delta"]))
            .field("temperature_norm", float(row["temperature_norm"]))
            .field("humidity_norm", float(row["humidity_norm"]))
            .time(ts.to_pydatetime(), WritePrecision.NS)
        )
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)


def main():
    print("Fetching raw data...")
    df = fetch_raw(minutes=30)
    if df.empty:
        print("No data. Hãy chạy simulator + collector trước.")
        return

    print(f"Loaded {len(df)} rows, devices: {df['device_id'].unique().tolist()}")

    for device_id, group in df.groupby("device_id"):
        print(f"\nProcessing {device_id} ({len(group)} rows)...")
        processed = process_device(group)
        print(f"  -> {len(processed)} rows after resample")
        write_processed(device_id, processed)
        print(f"  -> Written to InfluxDB: sensor_processed")

    print("\nDone.")


if __name__ == "__main__":
    main()