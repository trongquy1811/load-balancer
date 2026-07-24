import os
import uuid
import random
import logging
import hashlib
import datetime
import functools
import sqlite3
import time
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
import pandas as pd
import joblib
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG (Config & Logger)
# ==============================================================================
class Config:
    DB_DIR = "database"
    DB_NAME = "cloud.db"
    DB_PATH = os.path.join(DB_DIR, DB_NAME)
    
    MODEL_DIR = "model"
    MODEL_NAME = "random_forest.pkl"
    MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)
    
    DATA_DIR = "data"
    TRAIN_DATA_PATH = os.path.join(DATA_DIR, "train_data.csv")
    
    CPU_HIGH_THRESHOLD = 80.0
    RAM_HIGH_THRESHOLD = 80.0
    CPU_LOW_THRESHOLD = 30.0
    MAX_AUTO_SERVERS = 5
    
    FALLBACK_LEAST_CONN = "LEAST_CONNECTION"
    FALLBACK_ROUND_ROBIN = "ROUND_ROBIN"

# Khởi tạo các thư mục lưu trữ cốt lõi
for folder in [Config.DB_DIR, Config.MODEL_DIR, Config.DATA_DIR]:
    os.makedirs(folder, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CloudSystem")

# ==============================================================================
# 2. XỬ LÝ LỖI NGOẠI LỆ (Exception Handler)
# ==============================================================================
def safe_execution(fallback_value: Any):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Lỗi thực thi trong hàm {func.__name__}: {str(e)}")
                return fallback_value
        return wrapper
    return decorator

# ==============================================================================
# 3. CƠ SỞ DỮ LIỆU (Database Migration & Initializer)
# ==============================================================================
def get_connection():
    conn = sqlite3.connect(Config.DB_PATH, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Tối ưu hóa SQLite cho môi trường làm việc đa luồng
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Bảng người dùng (Phân quyền quản trị)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )""")
    
    # Bảng giám sát tài nguyên các Node Máy chủ ảo
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        cpu_usage REAL NOT NULL,
        ram_usage REAL NOT NULL,
        disk_usage REAL NOT NULL,
        network_usage REAL NOT NULL,
        queue_length INTEGER NOT NULL,
        response_time REAL NOT NULL,
        throughput REAL NOT NULL,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    
    # Bảng lưu lịch sử định tuyến Request
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests_log (
        request_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        status TEXT NOT NULL,
        allocated_server TEXT,
        routing_method TEXT,
        confidence_score REAL
    )""")
    
    # Tạo các node máy chủ mặc định ban đầu nếu cơ sở dữ liệu trống
    cursor.execute("SELECT COUNT(*) FROM servers")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.datetime.now().isoformat()
        default_servers = [
            ("SRV-01", "Application Server 1", 45.0, 50.0, 30.0, 150.0, 5, 120.0, 450.0, "ONLINE", now_str),
            ("SRV-02", "Application Server 2", 75.0, 82.0, 40.0, 300.0, 12, 280.0, 850.0, "ONLINE", now_str),
            ("SRV-03", "Application Server 3", 20.0, 35.0, 25.0, 80.0, 1, 60.0, 120.0, "ONLINE", now_str),
        ]
        cursor.executemany("INSERT INTO servers VALUES (?,?,?,?,?,?,?,?,?,?,?)", default_servers)
        
    conn.commit()
    conn.close()

# ==============================================================================
# 4. XÁC THỰC NGƯỜI DÙNG (Authentication)
# ==============================================================================
class AuthManager:
    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @classmethod
    def register_user(cls, username: str, password: str, role: str = "User") -> bool:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            pwd_hash = cls._hash_password(password)
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                           (username, pwd_hash, role))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        pwd_hash = cls._hash_password(password)
        cursor.execute("SELECT username, role FROM users WHERE username = ? AND password_hash = ?", 
                       (username, pwd_hash))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"username": row["username"], "role": row["role"]}
        return None

# ==============================================================================
# 5. GIÁM SÁT HẠ TẦNG & METADATA (Monitoring & Data Engineering)
# ==============================================================================
class CloudMonitoring:
    def collect_realtime_metrics(self) -> List[Dict[str, Any]]:
        """Cập nhật và trả về chỉ số thời gian thực từ DB mà không sử dụng cache có tác dụng phụ"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers")
        rows = cursor.fetchall()
        
        metrics = []
        for row in rows:
            # Mô phỏng sự biến thiên liên tục của tài nguyên mạng Cloud
            cpu_delta = random.uniform(-6.0, 6.0)
            new_cpu = max(5.0, min(100.0, row["cpu_usage"] + cpu_delta))
            
            ram_delta = random.uniform(-4.0, 4.0)
            new_ram = max(10.0, min(100.0, row["ram_usage"] + ram_delta))
            
            new_queue = max(0, int(row["queue_length"] + random.choice([-2, -1, 0, 1, 2])))
            new_rt = new_queue * random.uniform(15.0, 30.0) + 12.0
            new_tp = new_cpu * random.uniform(7.0, 11.0)
            
            timestamp = datetime.datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE servers 
                SET cpu_usage=?, ram_usage=?, queue_length=?, response_time=?, throughput=?, timestamp=?
                WHERE id=?
            """, (new_cpu, new_ram, new_queue, new_rt, new_tp, timestamp, row["id"]))
            
            metrics.append({
                "id": row["id"], 
                "name": row["name"], 
                "cpu_usage": new_cpu, 
                "ram_usage": new_ram,
                "disk_usage": row["disk_usage"], 
                "network_usage": row["network_usage"],
                "queue_length": new_queue, 
                "response_time": new_rt, 
                "throughput": new_tp,
                "status": row["status"], 
                "timestamp": timestamp
            })
            
        conn.commit()
        conn.close()
        return metrics

# ==============================================================================
# 6. MÔ HÌNH TRÍ TUỆ NHÂN TẠO RANDOM FOREST (Core Machine Learning)
# ==============================================================================
class RandomForestModelManager:
    def __init__(self):
        self.model_path = Config.MODEL_PATH
        self.clf = RandomForestClassifier(n_estimators=100, criterion='gini', random_state=42)

    def generate_synthetic_train_data(self):
        np.random.seed(42)
        records = 600
        
        # Lấy danh sách server hiện tại để gán nhãn chính xác
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM servers WHERE status = 'ONLINE'")
        server_ids = [r['id'] for r in cursor.fetchall()]
        conn.close()
        
        if not server_ids:
            server_ids = ["SRV-01", "SRV-02", "SRV-03"]

        data = {
            'cpu_usage': np.random.uniform(10, 95, records),
            'ram_usage': np.random.uniform(15, 95, records),
            'disk_usage': np.random.uniform(20, 80, records),
            'network_usage': np.random.uniform(50, 500, records),
            'queue_length': np.random.randint(0, 40, records),
            'response_time': np.random.uniform(10, 400, records),
            'throughput': np.random.uniform(100, 1000, records),
        }
        df = pd.DataFrame(data)
        
        # Gán nhãn server tối ưu dựa trên chỉ số tải tổng hợp
        labels = []
        for _, row in df.iterrows():
            if row['cpu_usage'] < 40 and row['queue_length'] < 8:
                labels.append(server_ids[-1] if len(server_ids) >= 3 else server_ids[0])
            elif row['cpu_usage'] < 75:
                labels.append(server_ids[0])
            else:
                labels.append(server_ids[1] if len(server_ids) >= 2 else server_ids[0])
        df['best_server'] = labels
        df.to_csv(Config.TRAIN_DATA_PATH, index=False)

    def train_and_save(self) -> dict:
        if not os.path.exists(Config.TRAIN_DATA_PATH):
            self.generate_synthetic_train_data()
            
        df = pd.read_csv(Config.TRAIN_DATA_PATH)
        feature_cols = ['cpu_usage', 'ram_usage', 'disk_usage', 'network_usage', 'queue_length', 'response_time', 'throughput']
        X = df[feature_cols]
        y = df['best_server']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.clf.fit(X_train, y_train)
        preds = self.clf.predict(X_test)
        
        metrics = {
            "accuracy": float(accuracy_score(y_test, preds)),
            "feature_importances": dict(zip(X.columns, [float(val) for val in self.clf.feature_importances_])),
            "matrix": confusion_matrix(y_test, preds).tolist()
        }
        
        joblib.dump(self.clf, self.model_path)
        # Làm mới Streamlit resource cache nếu có
        st.cache_resource.clear()
        return metrics

    def load_model(self) -> RandomForestClassifier:
        if not os.path.exists(self.model_path):
            self.train_and_save()
        return joblib.load(self.model_path)

@st.cache_resource
def get_cached_model():
    """Tải và lưu cache mô hình RF trong bộ nhớ RAM để tối ưu tốc độ dự đoán"""
    manager = RandomForestModelManager()
    return manager.load_model()

# ==============================================================================
# 7. CÂN BẰNG TẢI THÔNG MINH & ĐIỀU PHỐI (Load Balancer & Allocator Engine)
# ==============================================================================
class LoadBalancerCore:
    def __init__(self):
        self.model_manager = RandomForestModelManager()
        self.rr_index = 0

    def _get_active_servers(self) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE status = 'ONLINE'")
        servers = cursor.fetchall()
        conn.close()
        return servers

    @safe_execution(fallback_value=(None, "CRITICAL_FALLBACK", 0.0))
    def route_request(self, current_metrics: dict) -> Tuple[Optional[str], str, float]:
        active_servers = self._get_active_servers()
        if not active_servers:
            return None, "CRITICAL_FALLBACK", 0.0
            
        server_ids = [s["id"] for s in active_servers]
        features = [
            current_metrics.get('cpu_usage', 50.0), current_metrics.get('ram_usage', 50.0),
            current_metrics.get('disk_usage', 50.0), current_metrics.get('network_usage', 100.0),
            current_metrics.get('queue_length', 0), current_metrics.get('response_time', 50.0),
            current_metrics.get('throughput', 200.0)
        ]
        
        # 1. Thử nghiệm định tuyến lớp lõi AI (Random Forest)
        try:
            model = get_cached_model()
            arr = np.array(features).reshape(1, -1)
            pred = model.predict(arr)[0]
            probs = model.predict_proba(arr)[0]
            confidence = float(np.max(probs))
            
            if pred in server_ids:
                return str(pred), "RANDOM_FOREST", confidence
        except Exception as e:
            logger.warning(f"RF Prediction bypassed: {e}")
            
        # 2. Phòng vệ tầng 2: Least Connection (Chọn server có queue_length nhỏ nhất)
        try:
            least_conn_srv = min(active_servers, key=lambda x: (x["queue_length"], x["cpu_usage"]))
            return str(least_conn_srv["id"]), Config.FALLBACK_LEAST_CONN, 0.75
        except Exception:
            # 3. Phòng vệ tầng cuối: Round Robin
            srv_target = server_ids[self.rr_index % len(server_ids)]
            self.rr_index = (self.rr_index + 1) % len(server_ids)
            return str(srv_target), Config.FALLBACK_ROUND_ROBIN, 0.50

class RequestManager:
    @staticmethod
    def log_request(allocated_server: str, method: str, conf: float) -> str:
        conn = get_connection()
        cursor = conn.cursor()
        req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        ts = datetime.datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO requests_log (request_id, timestamp, status, allocated_server, routing_method, confidence_score)
            VALUES (?, ?, 'PROCESSED', ?, ?, ?)
        """, (req_id, ts, allocated_server, method, conf))
        
        cursor.execute("UPDATE servers SET queue_length = queue_length + 1 WHERE id = ?", (allocated_server,))
        conn.commit()
        conn.close()
        return req_id

# ==============================================================================
# 8. TỰ ĐỘNG CO GIÃN HẠ TẦNG & THỐNG KÊ (Auto-Scaling & Stats)
# ==============================================================================
class AutoScaler:
    @staticmethod
    def check_and_scale(avg_cpu: float) -> str:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Đếm số node tự động co giãn hiện tại
        cursor.execute("SELECT COUNT(*) FROM servers WHERE id LIKE 'SRV-AUTO-%'")
        auto_count = cursor.fetchone()[0]
        
        if avg_cpu > Config.CPU_HIGH_THRESHOLD:
            if auto_count < Config.MAX_AUTO_SERVERS:
                new_id = f"SRV-AUTO-{random.randint(10,99)}"
                cursor.execute("""
                    INSERT INTO servers VALUES (?, 'Dynamic Auto-Scale Node', 25.0, 30.0, 20.0, 60.0, 0, 25.0, 150.0, 'ONLINE', ?)
                """, (new_id, datetime.datetime.now().isoformat()))
                conn.commit()
                conn.close()
                return f"🚨 Tải Cluster cao ({avg_cpu:.1f}%)! Hệ thống đã kích hoạt Node mới: {new_id}"
            else:
                conn.close()
                return f"⚠️ Tải Cluster cao ({avg_cpu:.1f}%), nhưng đã đạt giới hạn tối đa ({Config.MAX_AUTO_SERVERS}) Node Auto-Scale."
            
        elif avg_cpu < Config.CPU_LOW_THRESHOLD:
            cursor.execute("SELECT id FROM servers WHERE id LIKE 'SRV-AUTO-%' LIMIT 1")
            target = cursor.fetchone()
            if target:
                node_id = target['id']
                cursor.execute("DELETE FROM servers WHERE id = ?", (node_id,))
                conn.commit()
                conn.close()
                return f"♻️ Tải hạ tầng thấp ({avg_cpu:.1f}%). Đã giải phóng bớt Node: {node_id}"
                
        conn.close()
        return f"✅ Hạ tầng hoạt động ổn định (CPU trung bình: {avg_cpu:.1f}%)."

class StatisticsManager:
    @staticmethod
    def get_kpis() -> dict:
        conn = get_connection()
        df_req = pd.read_sql_query("SELECT * FROM requests_log", conn)
        df_srv = pd.read_sql_query("SELECT * FROM servers", conn)
        conn.close()
        
        total = len(df_req)
        avg_cpu = float(df_srv['cpu_usage'].mean()) if not df_srv.empty else 0.0
        avg_ram = float(df_srv['ram_usage'].mean()) if not df_srv.empty else 0.0
        avg_rt = float(df_srv['response_time'].mean()) if not df_srv.empty else 0.0
        
        return {
            "total_requests": total,
            "avg_cpu": avg_cpu,
            "avg_ram": avg_ram,
            "avg_response_time": avg_rt,
            "server_count": len(df_srv)
        }

# ==============================================================================
# 9. GIAO DIỆN ĐỒ HỌA ĐIỀU KHIỂN TẬP TRUNG (Streamlit Main App)
# ==============================================================================
# Khởi tạo DB ban đầu
init_db()

st.set_page_config(
    page_title="Cloud Resource Allocator using RF",
    layout="wide",
    page_icon="☁️",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện giao diện hiện đại & chuyển động mượt mà
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .stMetric label {
        color: #94a3b8 !important;
        font-weight: 600;
    }
    .stMetric div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# Khai báo Session State cho người dùng
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = True
    st.session_state["username"] = "admin"
    st.session_state["role"] = "Admin"

# THANH MENU ĐIỀU HƯỚNG BÊN TRÁI (Sidebar)
st.sidebar.title("☁️ Cloud ML-Balancer")
st.sidebar.caption("Intelligent Multi-Agent & Machine Learning Load Balancing System")
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Tài khoản:** `{st.session_state['username']}`")
st.sidebar.write(f"🛡️ **Quyền hạn:** `{st.session_state['role']}`")
st.sidebar.markdown("---")

menu = st.sidebar.radio("📋 Menu Chức Năng", [
    "Dashboard Giám sát Tải", 
    "Điều hướng Khách hàng (Load Balancer)", 
    "Huấn luyện Mô hình AI", 
    "Lịch sử Nhật ký Hệ thống"
])

# KHỞI TẠO ĐỐI TƯỢNG ĐIỀU PHỐI VÀ THEO DÕI
monitor = CloudMonitoring()
lb_engine = LoadBalancerCore()

# --------------------------------------------------------------------------
# CHỨC NĂNG 1: DASHBOARD GIÁM SÁT TẢI THỜI GIAN THỰC
# --------------------------------------------------------------------------
if menu == "Dashboard Giám sát Tải":
    st.title("📊 Real-Time Cloud Infrastructure Dashboard")
    st.caption("Giám sát trạng thái hoạt động thực tế của các Node máy chủ ảo theo thời gian thực.")
    
    # Auto refresh switch
    col_ctrl1, col_ctrl2 = st.columns([1, 4])
    with col_ctrl1:
        auto_refresh = st.checkbox("🔄 Tự động làm mới", value=False)
    with col_ctrl2:
        if st.button("⚡ Làm mới dữ liệu ngay"):
            st.rerun()
            
    # Lấy dữ liệu động và tính toán KPI
    servers_list = monitor.collect_realtime_metrics()
    df_servers = pd.DataFrame(servers_list)
    kpis = StatisticsManager.get_kpis()
    
    # Hiển thị các Widget thẻ số liệu KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Requests Đã Xử Lý", kpis["total_requests"])
    c2.metric("Số Node Đang Online", kpis["server_count"])
    c3.metric("CPU Cluster Trung Bình", f"{kpis['avg_cpu']:.1f}%")
    c4.metric("Thời gian phản hồi TB", f"{kpis['avg_response_time']:.1f} ms")
    
    st.markdown("---")
    st.subheader("🖥️ Trạng thái chi tiết Virtual Nodes")
    
    # Custom format cho dataframe
    st.dataframe(
        df_servers[['id', 'name', 'cpu_usage', 'ram_usage', 'queue_length', 'response_time', 'throughput', 'status', 'timestamp']], 
        use_container_width=True,
        column_config={
            "cpu_usage": st.column_config.ProgressColumn("CPU (%)", format="%.1f%%", min_value=0, max_value=100),
            "ram_usage": st.column_config.ProgressColumn("RAM (%)", format="%.1f%%", min_value=0, max_value=100),
            "response_time": st.column_config.NumberColumn("Response Time (ms)", format="%.1f ms"),
            "throughput": st.column_config.NumberColumn("Throughput (req/s)", format="%.1f"),
        }
    )
    
    # Biểu đồ Plotly trực quan hóa tài nguyên
    st.markdown("### 📈 Biểu đồ Trực quan hóa Tiêu thụ Tài nguyên")
    fig_col1, fig_col2 = st.columns(2)
    
    with fig_col1:
        fig_cpu = px.bar(
            df_servers, x='id', y='cpu_usage', color='cpu_usage',
            title='Tỷ lệ Sử dụng CPU từng Node (%)', text_auto='.1f',
            color_continuous_scale='Reds'
        )
        fig_cpu.update_layout(template="plotly_dark")
        st.plotly_chart(fig_cpu, use_container_width=True)
        
    with fig_col2:
        fig_ram = px.bar(
            df_servers, x='id', y='ram_usage', color='ram_usage',
            title='Tỷ lệ Sử dụng RAM từng Node (%)', text_auto='.1f',
            color_continuous_scale='Blues'
        )
        fig_ram.update_layout(template="plotly_dark")
        st.plotly_chart(fig_ram, use_container_width=True)
    
    # Kiểm tra tự động co giãn hạ tầng (Auto Scaling)
    scale_message = AutoScaler.check_and_scale(kpis["avg_cpu"])
    st.info(scale_message)
    
    if auto_refresh:
        time.sleep(2)
        st.rerun()

# --------------------------------------------------------------------------
# CHỨC NĂNG 2: ĐIỀU HƯỚNG KHÁCH HÀNG (LOAD BALANCER)
# --------------------------------------------------------------------------
elif menu == "Điều hướng Khách hàng (Load Balancer)":
    st.title("🔀 Định tuyến & Cân bằng Tải Thông minh")
    st.write("Mô phỏng lưu lượng truy cập của client gửi tới hệ thống đám mây. Cơ chế phòng vệ 3 lớp: **Random Forest ML -> Least Connection -> Round Robin**.")
    
    col_sim1, col_sim2 = st.columns([2, 1])
    with col_sim1:
        st.markdown("#### ⚙️ Thông số Request Mô phỏng")
        req_cpu = st.slider("Mức độ tiêu tốn CPU yêu cầu (%)", 10.0, 100.0, 45.0)
        req_ram = st.slider("Mức độ tiêu tốn RAM yêu cầu (%)", 10.0, 100.0, 50.0)
        req_queue = st.slider("Độ dài hàng đợi hiện tại (Queue Length)", 0, 50, 5)
        
    with col_sim2:
        st.markdown("#### 🚀 Gửi Yêu cầu")
        send_btn = st.button("🔥 Gửi Client Request Tự động", use_container_width=True)
        send_custom_btn = st.button("🎯 Gửi Request với Thông số trên", use_container_width=True)

    if send_btn or send_custom_btn:
        if send_btn:
            mock_metrics = {
                'cpu_usage': random.uniform(15, 95),
                'ram_usage': random.uniform(20, 90),
                'disk_usage': 45.0,
                'network_usage': random.uniform(80, 450),
                'queue_length': random.randint(1, 25),
                'response_time': random.uniform(50, 250),
                'throughput': 400.0
            }
        else:
            mock_metrics = {
                'cpu_usage': req_cpu,
                'ram_usage': req_ram,
                'disk_usage': 45.0,
                'network_usage': 250.0,
                'queue_length': req_queue,
                'response_time': req_queue * 20.0 + 15.0,
                'throughput': 500.0
            }
            
        target_node, method_used, score = lb_engine.route_request(mock_metrics)
        if target_node:
            req_id = RequestManager.log_request(target_node, method_used, score)
            
            st.success(f"✅ Yêu cầu xử lý thành công! Mã Request: **{req_id}**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Node được Phân bổ", target_node)
            with col2:
                st.metric("Thuật toán Sử dụng", method_used)
            with col3:
                st.metric("Độ tin cậy AI (Confidence)", f"{score * 100:.1f}%")
                
            st.markdown("### 📋 Kế hoạch Cấp phát Tài nguyên Chi tiết")
            allocation_plan = {
                "request_id": req_id,
                "target_node": target_node,
                "routing_strategy": method_used,
                "confidence_score": f"{score:.4f}",
                "cpu_allocation": "High_Performance" if mock_metrics['cpu_usage'] < 70 else "Boost_Emergency",
                "allocated_ram_mb": 4096 if mock_metrics['ram_usage'] > 60 else 2048,
                "status": "PROCESSED"
            }
            st.json(allocation_plan)
        else:
            st.error("❌ Không thể phân bổ Node! Kiểm tra lại kết nối cơ sở dữ liệu hoặc trạng thái máy chủ.")

# --------------------------------------------------------------------------
# CHỨC NĂNG 3: HUẤN LUYỆN MÔ HÌNH AI (RANDOM FOREST)
# --------------------------------------------------------------------------
elif menu == "Huấn luyện Mô hình AI":
    st.title("🧠 Trung tâm Huấn luyện & Tối ưu Mô hình Random Forest")
    st.write("Hệ thống phân tích các tập dữ liệu lịch sử tải, xây dựng các cây quyết định song song và tính toán mức độ quan trọng của từng thuộc tính.")
    
    rf_manager = RandomForestModelManager()
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.info("Mô hình Random Forest sẽ học cách phân bổ lưu lượng tối ưu dựa trên CPU, RAM, Queue Length, Response Time và Throughput.")
    with col_t2:
        train_btn = st.button("🏋️ Huấn luyện lại (Retrain)", use_container_width=True)

    if train_btn:
        with st.spinner("Đang trích xuất dữ liệu, tối ưu hóa các node quyết định..."):
            metrics = rf_manager.train_and_save()
            st.balloons()
            st.success(f"🎯 Huấn luyện thành công! Độ chính xác (Accuracy): **{metrics['accuracy']*100:.2f}%**")
            
            st.markdown("### 📊 Mức độ Quan trọng Thuộc tính (Feature Importance)")
            df_imp = pd.DataFrame(
                list(metrics['feature_importances'].items()), 
                columns=['Thuộc tính', 'Độ quan trọng']
            ).sort_values(by='Độ quan trọng', ascending=True)
            
            fig_imp = px.bar(
                df_imp, x='Độ quan trọng', y='Thuộc tính', orientation='h',
                color='Độ quan trọng', color_continuous_scale='Viridis',
                title="Feature Importance Ranking"
            )
            fig_imp.update_layout(template="plotly_dark")
            st.plotly_chart(fig_imp, use_container_width=True)

# --------------------------------------------------------------------------
# CHỨC NĂNG 4: LỊCH SỬ NHẬT KÝ HỆ THỐNG
# --------------------------------------------------------------------------
elif menu == "Lịch sử Nhật ký Hệ thống":
    st.title("📜 Nhật ký Hệ thống & Lịch sử Định tuyến")
    st.write("Tra cứu lịch sử phân phối yêu cầu và dấu vết định tuyến lưu trong Cơ sở dữ liệu SQLite:")
    
    conn = get_connection()
    df_logs = pd.read_sql_query("SELECT * FROM requests_log ORDER BY timestamp DESC LIMIT 200", conn)
    conn.close()
    
    if df_logs.empty:
        st.info("Chưa có lịch sử định tuyến nào được ghi nhận.")
    else:
        c_filter1, c_filter2 = st.columns(2)
        with c_filter1:
            method_filter = st.multiselect("Lọc theo Thuật toán", options=df_logs['routing_method'].unique().tolist())
        with c_filter2:
            server_filter = st.multiselect("Lọc theo Server", options=df_logs['allocated_server'].unique().tolist())
            
        filtered_df = df_logs.copy()
        if method_filter:
            filtered_df = filtered_df[filtered_df['routing_method'].isin(method_filter)]
        if server_filter:
            filtered_df = filtered_df[filtered_df['allocated_server'].isin(server_filter)]
            
        st.dataframe(filtered_df, use_container_width=True)
        
        # Nút tải xuống CSV
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Tải xuống Nhật ký (CSV)",
            data=csv_data,
            file_name="requests_log.csv",
            mime="text/csv"
        )