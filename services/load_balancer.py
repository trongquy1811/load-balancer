import uuid
import datetime
from typing import Tuple, Optional, Dict, Any
from config import Config
from database.db import get_db_connection
from models.random_forest import RandomForestModelManager
from utils.logger import logger

class LoadBalancerService:
    """Bộ điều phối cân bằng tải hỗ trợ 3 thuật toán: Random Forest, Least Connection, Round Robin."""
    
    def __init__(self):
        self.rf_manager = RandomForestModelManager()
        self.rr_index = 0

    def _get_active_servers(self) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE status = 'ONLINE'")
        servers = cursor.fetchall()
        conn.close()
        return servers

    def route_request(self, req_metrics: Dict[str, Any], method: Optional[str] = None) -> Tuple[Optional[str], str, float]:
        """Điều hướng request tới server tối ưu nhất dựa trên thuật toán được chỉ định hoặc tự động chọn."""
        active_servers = self._get_active_servers()
        if not active_servers:
            logger.error("Không có máy chủ ONLINE nào khả dụng để nhận request!")
            return None, "NONE_AVAILABLE", 0.0
            
        server_ids = [s["id"] for s in active_servers]
        
        # Nếu chỉ định cụ thể thuật toán LEAST_CONNECTION
        if method == Config.METHOD_LEAST_CONN:
            least_conn_srv = min(active_servers, key=lambda x: (x["queue_length"], x["cpu_usage"]))
            return str(least_conn_srv["id"]), Config.METHOD_LEAST_CONN, 0.85
            
        # Nếu chỉ định cụ thể thuật toán ROUND_ROBIN
        elif method == Config.METHOD_ROUND_ROBIN:
            target_id = server_ids[self.rr_index % len(server_ids)]
            self.rr_index = (self.rr_index + 1) % len(server_ids)
            return str(target_id), Config.METHOD_ROUND_ROBIN, 0.60
            
        # Mặc định thử nghiệm thuật toán RANDOM_FOREST AI
        features = [
            req_metrics.get('cpu_usage', 50.0), req_metrics.get('ram_usage', 50.0),
            req_metrics.get('disk_usage', 50.0), req_metrics.get('network_usage', 100.0),
            req_metrics.get('queue_length', 0), req_metrics.get('response_time', 50.0),
            req_metrics.get('throughput', 200.0)
        ]
        
        try:
            pred_server, confidence = self.rf_manager.predict(features)
            if pred_server in server_ids:
                return pred_server, Config.METHOD_RANDOM_FOREST, confidence
        except Exception as e:
            logger.warning(f"RF prediction fallback triggered: {e}")
            
        # Phòng vệ 1: Least Connection
        try:
            least_conn_srv = min(active_servers, key=lambda x: (x["queue_length"], x["cpu_usage"]))
            return str(least_conn_srv["id"]), Config.METHOD_LEAST_CONN, 0.75
        except Exception:
            # Phòng vệ 2: Round Robin
            target_id = server_ids[self.rr_index % len(server_ids)]
            self.rr_index = (self.rr_index + 1) % len(server_ids)
            return str(target_id), Config.METHOD_ROUND_ROBIN, 0.50

    def log_and_execute_request(self, allocated_server: str, method: str, confidence: float, req_metrics: Dict[str, Any]) -> str:
        """Ghi nhận request vào cơ sở dữ liệu SQLite và cập nhật tải cho server được phân bổ."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        ts = datetime.datetime.now().isoformat()
        
        cpu_req = float(req_metrics.get('cpu_usage', 30.0))
        ram_req = float(req_metrics.get('ram_usage', 30.0))
        q_len = int(req_metrics.get('queue_length', 1))
        rt = float(req_metrics.get('response_time', q_len * 15.0 + 10.0))
        
        cursor.execute("""
            INSERT INTO requests_log 
            (request_id, timestamp, status, allocated_server, routing_method, confidence_score, cpu_req, ram_req, queue_length, response_time)
            VALUES (?, ?, 'PROCESSED', ?, ?, ?, ?, ?, ?, ?)
        """, (req_id, ts, allocated_server, method, confidence, cpu_req, ram_req, q_len, rt))
        
        # Cập nhật hàng đợi và độ trễ phản hồi của máy chủ
        cursor.execute("""
            UPDATE servers 
            SET queue_length = queue_length + 1,
                response_time = response_time + 5.0
            WHERE id = ?
        """, (allocated_server,))
        
        conn.commit()
        conn.close()
        logger.info(f"Đã phân bổ {req_id} tới {allocated_server} bằng thuật toán {method} (Confidence: {confidence:.2f})")
        return req_id
