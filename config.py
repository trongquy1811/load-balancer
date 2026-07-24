import os

class Config:
    """Cấu hình hệ thống Cloud Resource Manager & Load Balancer."""
    
    # Đường dẫn thư mục
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_DIR = os.path.join(BASE_DIR, "database")
    MODEL_DIR = os.path.join(BASE_DIR, "models")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOG_DIR = os.path.join(BASE_DIR, "logs")

    # Đường dẫn tập tin
    DB_NAME = "cloud.db"
    DB_PATH = os.path.join(DB_DIR, DB_NAME)
    
    MODEL_NAME = "random_forest.pkl"
    MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)
    
    TRAIN_DATA_PATH = os.path.join(DATA_DIR, "train_data.csv")

    # Ngưỡng tự động co giãn (Auto Scaling Thresholds)
    CPU_HIGH_THRESHOLD = 80.0
    CPU_LOW_THRESHOLD = 20.0
    MIN_SERVERS = 2
    MAX_SERVERS = 10

    # Thuật toán định tuyến (Routing Methods)
    METHOD_RANDOM_FOREST = "RANDOM_FOREST"
    METHOD_LEAST_CONN = "LEAST_CONNECTION"
    METHOD_ROUND_ROBIN = "ROUND_ROBIN"

# Tự động tạo các thư mục lưu trữ nếu chưa tồn tại
for directory in [Config.DB_DIR, Config.MODEL_DIR, Config.DATA_DIR, Config.LOG_DIR]:
    os.makedirs(directory, exist_ok=True)
