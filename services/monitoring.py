import random
import datetime
from typing import List, Dict, Any
from database.db import get_db_connection

class CloudMonitoring:
    """Thu thập và mô phỏng chỉ số thời gian thực từ các Node máy chủ ảo."""
    
    def collect_realtime_metrics(self) -> List[Dict[str, Any]]:
        """Cập nhật biến thiên tài nguyên của máy chủ và trả về danh sách chỉ số."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers")
        rows = cursor.fetchall()
        
        metrics = []
        for row in rows:
            if row["status"] != "ONLINE":
                metrics.append(dict(row))
                continue
                
            # Mô phỏng sự biến thiên liên tục của chỉ số máy chủ
            cpu_delta = random.uniform(-5.0, 5.0)
            new_cpu = max(5.0, min(100.0, row["cpu_usage"] + cpu_delta))
            
            ram_delta = random.uniform(-3.0, 3.0)
            new_ram = max(10.0, min(100.0, row["ram_usage"] + ram_delta))
            
            new_queue = max(0, int(row["queue_length"] + random.choice([-2, -1, 0, 1, 2])))
            new_rt = max(10.0, new_queue * random.uniform(15.0, 25.0) + 12.0)
            new_tp = max(50.0, new_cpu * random.uniform(7.0, 11.0))
            
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

    def get_cluster_summary((self) -> Dict[str, Any]:
        """Tính toán tổng quan chỉ số toàn cụm máy chủ."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE status = 'ONLINE'")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"server_count": 0, "avg_cpu": 0.0, "avg_ram": 0.0, "avg_response_time": 0.0, "total_throughput": 0.0}
            
        cpus = [r["cpu_usage"] for r in rows]
        rams = [r["ram_usage"] for r in rows]
        rts = [r["response_time"] for r in rows]
        tps = [r["throughput"] for r in rows]
        
        return {
            "server_count": len(rows),
            "avg_cpu": float(sum(cpus) / len(cpus)),
            "avg_ram": float(sum(rams) / len(rams)),
            "avg_response_time": float(sum(rts) / len(rts)),
            "total_throughput": float(sum(tps))
        }
