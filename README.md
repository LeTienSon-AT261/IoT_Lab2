# IoT Lab 2 — Thu thập, Lưu trữ và Tiền xử lý dữ liệu IoT

**Học phần:** IoT và Ứng dụng (INT14149)
**Sinh viên:** Lê Tiến Sơn — B23DCAT261

---

## 1. Giới thiệu

Pipeline IoT hoàn chỉnh thu thập dữ liệu cảm biến (nhiệt độ, độ ẩm, ánh sáng) qua MQTT, lưu vào InfluxDB 2.x, tiền xử lý và trực quan hóa real-time bằng Grafana.

Kiến trúc:

    Simulator/ESP32 → MQTT (Mosquitto) → Collector (Python)
        → InfluxDB 2.x → Preprocess → Grafana Dashboard

---

## 2. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| MQTT Broker | Eclipse Mosquitto 2 |
| Database | InfluxDB 2.7 (time-series) |
| Ngôn ngữ | Python 3.10+ |
| Thư viện | paho-mqtt, influxdb-client, pandas, numpy, scikit-learn, streamlit |
| Dashboard | Grafana + Streamlit |
| Triển khai | Docker Compose |

---

## 3. Yêu cầu hệ thống

- Docker Desktop (đã bật WSL2 backend)
- Python 3.10+
- Git
- VS Code (khuyến nghị)

---

## 4. Cấu trúc thư mục

    IoT_Lab2/
    ├── collector/
    │   └── collector.py          # Subscribe MQTT, validate, ghi InfluxDB
    ├── dashboard/
    │   └── streamlit_app.py      # Dashboard Streamlit
    ├── firmware/
    │   └── simulator.py          # Giả lập ESP32 publish dữ liệu
    ├── mosquitto/
    │   └── config/
    │       └── mosquitto.conf    # Cấu hình MQTT broker
    ├── preprocessing/
    │   ├── preprocess.py         # Tiền xử lý dữ liệu
    │   └── latency_stats.py      # Thống kê độ trễ
    ├── .env.example
    ├── .gitignore
    ├── docker-compose.yml
    ├── requirements.txt
    └── README.md

---

## 5. Hướng dẫn chạy

### 5.1. Khởi động hạ tầng Docker

    cd C:\IoT_Lab2
    docker compose up -d
    docker ps

Phải thấy 3 container mosquitto, influxdb, grafana đều Up.

### 5.2. Cài môi trường Python

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt

### 5.3. Cấu hình biến môi trường

    copy .env.example .env

Nội dung .env:

    MQTT_BROKER=localhost
    MQTT_PORT=1883
    MQTT_TOPIC=iot/+/+/data
    INFLUX_URL=http://localhost:8086
    INFLUX_TOKEN=my-super-secret-token
    INFLUX_ORG=iot-lab
    INFLUX_BUCKET=iot_data

### 5.4. Chạy pipeline

Mở 3 terminal, mỗi terminal activate .venv:

Terminal 1 — Simulator:

    python firmware/simulator.py

Terminal 2 — Collector:

    python collector/collector.py

Đợi 5–10 phút cho dữ liệu tích lũy.

Terminal 3 — Preprocess:

    python preprocessing/preprocess.py

### 5.5. Đo latency

    python preprocessing/latency_stats.py

---

## 6. Dashboard

### Grafana

- URL: http://localhost:3000
- Đăng nhập: admin / admin
- Datasource: InfluxDB, URL http://influxdb:8086, org iot-lab, bucket iot_data
- Dashboard gồm 5 panel: Raw Temperature & Humidity, Light Intensity, End-to-End Latency, Processed vs Rolling Mean, Latest Temperature (Stat)

### Streamlit (tùy chọn)

    streamlit run dashboard/streamlit_app.py

Mở http://localhost:8501.

---

## 7. Schema Database

| Measurement | Tags | Fields | Retention |
|---|---|---|---|
| sensor_raw | device_id | temperature, humidity, light | 7 ngày |
| sensor_processed | device_id | temperature, humidity, light, temp_roll_mean_5, hum_roll_mean_5, temp_delta, temperature_norm, humidity_norm | 7 ngày |
| latency | device_id | end_to_end_ms | 7 ngày |

---

## 8. Xử lý sự cố

| Lỗi | Cách sửa |
|---|---|
| Docker Desktop is unable to start | Bật ảo hóa trong BIOS, chạy bcdedit /set hypervisorlaunchtype Auto, wsl --update |
| InfluxDB báo 401 Unauthorized | Lấy token thật từ InfluxDB UI → cập nhật .env → restart collector |
| Collector không nhận MQTT | Kiểm tra topic simulator khớp pattern iot/+/+/data |
| Grafana không thấy dữ liệu | Đổi datasource URL thành http://influxdb:8086 |

---

## 9. Tác giả

- Họ tên: Lê Tiến Sơn
- MSSV: B23DCAT261
- Học phần: IoT và Ứng dụng (INT14149)

---

## 10. Tài liệu tham khảo

- InfluxDB Documentation: https://docs.influxdata.com/influxdb/v2/
- Mosquitto MQTT Broker: https://mosquitto.org/documentation/
- Grafana Documentation: https://grafana.com/docs/
- Paho MQTT Python Client: https://eclipse.dev/paho/clients/python/
- Flux Language Reference: https://docs.influxdata.com/flux/