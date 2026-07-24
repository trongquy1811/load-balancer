# ☁️ Cloud Resource Manager & Intelligent Load Balancer Simulation Suite

Dự án Mô phỏng Quản lý Tài nguyên Hạ tầng Đám mây, Cân bằng Tải Thông minh dựa trên Machine Learning (**Random Forest Classifier**), Tự động Co giãn Hạ tầng (**Auto Scaling**) trên giao diện ứng dụng web **Streamlit**.

---

## 🌟 Các Tính Năng Nổi Bật (Key Features)

### 1. 📊 Real-Time Cloud Infrastructure Dashboard
- Cập nhật tự động các chỉ số hạ tầng đám mây: CPU, RAM, Disk, Network, Throughput, Response Time, Active Requests.
- Trực quan hóa dữ liệu sinh động với các biểu đồ tương tác Plotly (Dark Mode).

### 2. 🚀 Load Test Simulation (Mô phỏng Tải Song Song)
- Cung cấp các nút khởi tạo nhanh: **Generate 10 Requests**, **100 Requests**, **500 Requests**, và **1000 Requests**.
- Xử lý đồng thời đa luồng (Multi-threading) qua 3 bộ cân bằng tải: Random Forest AI, Least Connection, Round Robin.
- Cập nhật số liệu máy chủ thời gian thực, lưu vết nhật ký vào cơ sở dữ liệu SQLite và hiển thị thanh tiến trình trực quan.

### 3. ⚖️ Performance Comparison Page (So sánh Hiệu năng Thuật toán)
- So sánh đối đầu trực tiếp 3 thuật toán: **Random Forest AI**, **Least Connection**, và **Round Robin**.
- Trực quan hóa bằng biểu đồ Plotly: **Average Response Time**, **Throughput**, **CPU Utilization**, **Load Distribution**, và **Success Rate**.

### 4. 📈 Auto Scaling Visualization (Trực quan hóa Co giãn Hạ tầng)
- Quản lý cụm máy chủ thời gian thực (`Node 1`, `Node 2`, ...).
- **Scale Up (CPU > 80%)**: Tự động tạo thêm Node máy chủ mới và hiển thị thông báo `"New server has been created."`.
- **Scale Down (CPU < 20%)**: Tự động giải phóng Node nhàn rỗi và hiển thị thông báo `"Server has been removed."`.
- Biểu đồ Plotly diễn biến quy mô Cluster và lịch sử các sự kiện co giãn.

### 5. 🧠 Machine Learning Model Evaluation
- Đánh giá chi tiết mô hình Random Forest Classifier: **Accuracy, Precision, Recall, F1 Score, Confusion Matrix Heatmap, Classification Report, Feature Importances**.

### 6. 📜 Request History & Logs
- Bộ lọc nhật ký đa chiều, tra cứu theo ID/Server/Thuật toán và xuất dữ liệu dạng CSV.

---

## 🚀 Hướng Dẫn Chạy Ứng Dụng (Quick Start)

### 1. Cài đặt các thư viện phụ thuộc:
```bash
pip install -r requirements.txt
```

### 2. Chạy ứng dụng Streamlit Dashboard:
```bash
streamlit run app.py
```
Ứng dụng sẽ tự động khởi chạy tại địa chỉ: `http://localhost:8501`

---

## 📁 Cấu Trúc Thư Mục Dự Án (Project Architecture)

```
load-balancer/
├── app.py               # Giao diện chính Streamlit Dashboard
├── config.py            # Cấu hình tham số và ngưỡng hệ thống
├── requirements.txt     # Danh sách phụ thuộc Python
├── README.md            # Tài liệu hướng dẫn sử dụng
│
├── database/            # Quản lý kết nối & schema SQLite (WAL mode)
│   └── db.py
├── models/              # Mô hình Machine Learning Random Forest
│   └── random_forest.py
├── services/            # Tầng xử lý nghiệp vụ Cloud Services
│   ├── auth.py          # Quản lý tài khoản
│   ├── monitoring.py    # Giám sát chỉ số realtime
│   ├── load_balancer.py # Bộ cân bằng tải 3 tầng
│   ├── auto_scaler.py   # Bộ tự động co giãn hạ tầng
│   └── simulator.py     # Bộ mô phỏng tải song song
└── utils/               # Công cụ Logging hệ thống
    └── logger.py
```