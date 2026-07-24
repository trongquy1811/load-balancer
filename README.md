# ☁️ Cloud Resource Manager & Intelligent Load Balancer Simulation Suite

Dự án Mô phỏng Quản lý Tài nguyên Hạ tầng Đám mây, Cân bằng Tải Thông minh dựa trên Machine Learning (**Random Forest Classifier**), Tự động Co giãn Hạ tầng (**Auto Scaling**) và Giao diện **Streamlit** kết hợp **FastAPI REST API**.

---

## 🌟 5 Tính Năng Mở Rộng Nổi Bật (Core Extended Features)

### 1. 🚀 Load Test Simulation (Mô phỏng Tải Song Song)
- Cung cấp các nút khởi tạo nhanh: **Generate 10 Requests**, **100 Requests**, **500 Requests**, và **1000 Requests**.
- Xử lý đồng thời đa luồng (Multi-threading) qua 3 bộ cân bằng tải: Random Forest AI, Least Connection, Round Robin.
- Cập nhật số liệu máy chủ thời gian thực, lưu vết nhật ký vào cơ sở dữ liệu SQLite và hiển thị thanh tiến trình trực quan.

### 2. ⚖️ Performance Comparison Page (So sánh Hiệu năng Thuật toán)
- So sánh đối đầu trực tiếp 3 thuật toán: **Random Forest AI**, **Least Connection**, và **Round Robin**.
- Trực quan hóa bằng biểu đồ Plotly: **Average Response Time**, **Throughput**, **CPU Utilization**, **Load Distribution**, và **Success Rate**.

### 3. 📈 Auto Scaling Visualization (Trực quan hóa Co giãn Hạ tầng)
- Quản lý cụm máy chủ thời gian thực (`Node 1`, `Node 2`, ...).
- **Scale Up (CPU > 80%)**: Tự động tạo thêm Node máy chủ mới và hiển thị thông báo `"New server has been created."`.
- **Scale Down (CPU < 20%)**: Tự động giải phóng Node nhàn rỗi và hiển thị thông báo `"Server has been removed."`.
- Biểu đồ Plotly diễn biến quy mô Cluster và lịch sử các sự kiện co giãn.

### 4. ⚡ REST API sử dụng FastAPI
- Cung cấp dịch vụ backend RESTful với các endpoint chuẩn Pydantic JSON:
  - `GET /servers`: Trích xuất danh sách tất cả các server nodes.
  - `GET /metrics`: Trích xuất chỉ số tổng quan toàn cụm.
  - `POST /predict`: Dự đoán máy chủ tối ưu bằng mô hình Random Forest.
  - `POST /requests`: Khởi tạo và định tuyến client request mới.
  - `POST /train`: Huấn luyện lại mô hình Machine Learning.
  - `GET /history`: Truy vấn nhật ký lịch sử request.

### 5. 📚 Tự Động Tạo Tài Liệu API (Swagger UI & ReDoc)
- **Swagger UI Interactive**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

## 🚀 Hướng Dẫn Chạy Ứng Dụng (Quick Start)

### 1. Cài đặt các thư viện phụ thuộc:
```bash
pip install -r requirements.txt
```

### 2. Chạy ứng dụng Giao diện Streamlit Dashboard:
```bash
streamlit run app.py
```
Ứng dụng sẽ chạy tại địa chỉ: `http://localhost:8501`

### 3. Chạy dịch vụ Backend FastAPI REST API:
```bash
uvicorn api.main:app --reload
```
Dịch vụ REST API sẽ chạy tại địa chỉ: `http://localhost:8000`  
Xem tài liệu Swagger UI tại: `http://localhost:8000/docs`

---

## 📁 Cấu Trúc Thư Mục Dự Án (Project Architecture)

```
load-balancer/
├── app.py               # Giao diện chính Streamlit Dashboard
├── config.py            # Cấu hình tham số và ngưỡng hệ thống
├── requirements.txt     # Danh sách phụ thuộc Python
├── README.md            # Tài liệu hướng dẫn sử dụng
│
├── database/            # Quản lý kết nối & schema SQLite
│   └── db.py
├── models/              # Mô hình Machine Learning Random Forest
│   └── random_forest.py
├── services/            # Tầng xử lý nghiệp vụ Cloud Services
│   ├── auth.py          # Quản lý người dùng
│   ├── monitoring.py    # Giám sát chỉ số realtime
│   ├── load_balancer.py # Bộ cân bằng tải 3 tầng
│   ├── auto_scaler.py   # Bộ tự động co giãn hạ tầng
│   └── simulator.py     # Bộ mô phỏng tải song song
├── api/                 # Tầng REST API với FastAPI
│   └── main.py
└── utils/               # Công cụ hỗ trợ và Logging
    └── logger.py
```