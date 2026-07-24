import random
import datetime
from typing import Tuple, List, Dict, Any
from config import Config
from database.db import get_db_connection
from utils.logger import logger

class AutoScalerService:
    """Quản lý tính năng Tự động Co giãn (Auto Scaling) hạ tầng máy chủ ảo."""
    
    @staticmethod
    def check_and_scale(avg_cpu: float) -> Tuple[str, List[Dict[str, Any]]]:
        """Kiểm tra chỉ số CPU trung bình của cluster và kích hoạt tạo/giải phóng máy chủ khi vượt ngưỡng."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM servers WHERE status = 'ONLINE'")
        online_servers = cursor.fetchall()
        current_size = len(online_servers)
        
        messages = []

        # 1. Trường hợp CPU > 80%: Thêm máy chủ mới
        if avg_cpu > Config.CPU_HIGH_THRESHOLD:
            if current_size < Config.MAX_SERVERS:
                new_id = f"SRV-AUTO-{random.randint(10, 99)}"
                new_name = f"Auto-Scaled Server {new_id[-2:]}"
                now_str = datetime.datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO servers VALUES (?, ?, 25.0, 30.0, 20.0, 60.0, 0, 20.0, 150.0, 'ONLINE', ?)
                """, (new_id, new_name, now_str))
                
                # Ghi nhật ký sự kiện scaling
                cursor.execute("""
                    INSERT INTO scaling_events (event_type, server_id, reason, cpu_avg, cluster_size, timestamp)
                    VALUES ('SCALE_UP', ?, 'CPU Utilization > 80%', ?, ?, ?)
                """, (new_id, avg_cpu, current_size + 1, now_str))
                
                msg = f"New server has been created. (ID: {new_id})"
                messages.append({"type": "SCALE_UP", "message": msg, "server_id": new_id})
                logger.info(f"Auto-Scale UP: {msg}")
            else:
                msg = f"CPU High ({avg_cpu:.1f}%), reached maximum limit of {Config.MAX_SERVERS} servers."
                messages.append({"type": "WARNING", "message": msg, "server_id": ""})

        # 2. Trường hợp CPU < 20%: Thu hồi máy chủ nhàn rỗi
        elif avg_cpu < Config.CPU_LOW_THRESHOLD:
            if current_size > Config.MIN_SERVERS:
                cursor.execute("SELECT id FROM servers WHERE id LIKE 'SRV-AUTO-%' LIMIT 1")
                auto_target = cursor.fetchone()
                
                target_id = auto_target['id'] if auto_target else online_servers[-1]['id']
                now_str = datetime.datetime.now().isoformat()
                
                cursor.execute("DELETE FROM servers WHERE id = ?", (target_id,))
                
                cursor.execute("""
                    INSERT INTO scaling_events (event_type, server_id, reason, cpu_avg, cluster_size, timestamp)
                    VALUES ('SCALE_DOWN', ?, 'CPU Utilization < 20%', ?, ?, ?)
                """, (target_id, avg_cpu, current_size - 1, now_str))
                
                msg = f"Server has been removed. (ID: {target_id})"
                messages.append({"type": "SCALE_DOWN", "message": msg, "server_id": target_id})
                logger.info(f"Auto-Scale DOWN: {msg}")
            else:
                msg = f"CPU Low ({avg_cpu:.1f}%), reached minimum limit of {Config.MIN_SERVERS} servers."
                messages.append({"type": "INFO", "message": msg, "server_id": ""})

        conn.commit()
        conn.close()
        
        summary_status = f"Cluster Size: {current_size} Nodes | Avg CPU: {avg_cpu:.1f}%"
        return summary_status, messages

    @staticmethod
    def get_scaling_history(limit: int = 50) -> List[Dict[str, Any]]:
        """Lấy lịch sử các sự kiện co giãn đã diễn ra."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scaling_events ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
