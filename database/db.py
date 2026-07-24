import sqlite3
import datetime
from config import Config
from utils.logger import logger

def get_db_connection() -> sqlite3.Connection:
    """Khởi tạo và trả về kết nối SQLite an toàn đa luồng."""
    conn = sqlite3.connect(Config.DB_PATH, timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Kích hoạt WAL mode hỗ trợ đọc/ghi đồng thời
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """Khởi tạo cấu trúc bảng SQLite và nạp dữ liệu mẫu ban đầu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Bảng người dùng (User Auth)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )""")
    
    # Bảng hạ tầng máy chủ ảo (Servers)
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
    
    # Bảng nhật ký định tuyến yêu cầu (Requests Log)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests_log (
        request_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        status TEXT NOT NULL,
        allocated_server TEXT,
        routing_method TEXT,
        confidence_score REAL,
        cpu_req REAL DEFAULT 0.0,
        ram_req REAL DEFAULT 0.0,
        queue_length INTEGER DEFAULT 0,
        response_time REAL DEFAULT 0.0
    )""")
    
    # Bảng lưu trữ nhật ký sự kiện co giãn (Scaling Events Log)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scaling_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        server_id TEXT NOT NULL,
        reason TEXT NOT NULL,
        cpu_avg REAL NOT NULL,
        cluster_size INTEGER NOT NULL,
        timestamp TEXT NOT NULL
    )""")

    # Tạo các node máy chủ mặc định nếu DB chưa có máy chủ nào
    cursor.execute("SELECT COUNT(*) FROM servers")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.datetime.now().isoformat()
        default_servers = [
            ("SRV-01", "Application Server 1", 45.0, 50.0, 30.0, 150.0, 5, 120.0, 450.0, "ONLINE", now_str),
            ("SRV-02", "Application Server 2", 75.0, 82.0, 40.0, 300.0, 12, 280.0, 850.0, "ONLINE", now_str),
            ("SRV-03", "Application Server 3", 20.0, 35.0, 25.0, 80.0, 1, 60.0, 120.0, "ONLINE", now_str),
        ]
        cursor.executemany("INSERT INTO servers VALUES (?,?,?,?,?,?,?,?,?,?,?)", default_servers)
        logger.info("Đã nạp 3 máy chủ ảo mặc định vào cơ sở dữ liệu.")
        
    conn.commit()
    conn.close()
