import os
import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

load_dotenv()

client = InfluxDBClient(
    url=os.getenv("INFLUX_URL"),
    token=os.getenv("INFLUX_TOKEN"),
    org=os.getenv("INFLUX_ORG"),
)
bucket = os.getenv("INFLUX_BUCKET")

query = f'''
from(bucket: "{bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "latency")
  |> filter(fn: (r) => r._field == "end_to_end_ms")
'''
df = client.query_api().query_data_frame(query)
if isinstance(df, list):
    df = pd.concat(df, ignore_index=True) if df else pd.DataFrame()

if df.empty:
    print("No latency data")
else:
    s = df["_value"]
    print("=== Latency (ms) ===")
    print(f"count : {len(s)}")
    print(f"mean  : {s.mean():.2f}")
    print(f"min   : {s.min():.2f}")
    print(f"max   : {s.max():.2f}")
    print(f"p50   : {s.quantile(0.5):.2f}")
    print(f"p95   : {s.quantile(0.95):.2f}")
    print(f"p99   : {s.quantile(0.99):.2f}")