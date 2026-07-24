import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Callable
from services.load_balancer import LoadBalancerService
from database.db import get_db_connection
from utils.logger import logger

class LoadTestingSimulator:
    """Bộ mô phỏng tải song song (10, 100, 500, 1000 requests) và so sánh hiệu năng thuật toán."""
    
    def __init__(self):
        self.lb_service = LoadBalancerService()

    def generate_random_request_metrics(self) -> Dict[str, Any]:
        """Tạo dữ liệu tải ngẫu nhiên đại diện cho client request."""
        return {
            'cpu_usage': random.uniform(15.0, 95.0),
            'ram_usage': random.uniform(20.0, 90.0),
            'disk_usage': random.uniform(20.0, 70.0),
            'network_usage': random.uniform(80.0, 450.0),
            'queue_length': random.randint(1, 25),
            'response_time': random.uniform(20.0, 250.0),
            'throughput': random.uniform(100.0, 800.0)
        }

    def run_simulation(self, count: int, method: str = None, progress_callback: Callable[[float], None] = None) -> Dict[str, Any]:
        """Thực thi mô phỏng luồng request đồng thời và trả về kết quả đo đạc."""
        logger.info(f"Bắt đầu chạy Load Test với {count} requests...")
        start_time = time.time()
        
        results = []
        completed = 0

        def process_single_request(_):
            req_m = self.generate_random_request_metrics()
            target_node, method_used, score = self.lb_service.route_request(req_m, method=method)
            if target_node:
                req_id = self.lb_service.log_and_execute_request(target_node, method_used, score, req_m)
                return {
                    "request_id": req_id,
                    "target_node": target_node,
                    "method": method_used,
                    "score": score,
                    "response_time": req_m['response_time'],
                    "cpu_req": req_m['cpu_usage'],
                    "success": True
                }
            return {"success": False}

        # Sử dụng ThreadPoolExecutor để giả lập truy cập đồng thời từ người dùng
        workers = min(32, max(4, count // 10))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(process_single_request, i) for i in range(count)]
            for future in as_completed(futures):
                res = future.result()
                results.append(res)
                completed += 1
                if progress_callback:
                    progress_callback(completed / count)

        elapsed = time.time() - start_time
        successful = [r for r in results if r.get("success")]
        
        response_times = [r["response_time"] for r in successful]
        avg_rt = float(sum(response_times) / len(response_times)) if response_times else 0.0
        success_rate = (len(successful) / count) * 100.0 if count > 0 else 0.0
        throughput = count / elapsed if elapsed > 0 else 0.0

        # Phân phối tải trọng giữa các server
        node_counts = {}
        for r in successful:
            node = r["target_node"]
            node_counts[node] = node_counts.get(node, 0) + 1

        summary = {
            "total_requests": count,
            "successful_requests": len(successful),
            "success_rate": success_rate,
            "total_time_seconds": elapsed,
            "avg_response_time": avg_rt,
            "throughput_req_per_sec": throughput,
            "load_distribution": node_counts
        }
        
        logger.info(f"Hoàn thành Load Test {count} requests trong {elapsed:.2f}s. Throughput: {throughput:.1f} req/s")
        return summary

    def compare_algorithms(self, req_count_per_algo: int = 100) -> Dict[str, Dict[str, Any]]:
        """Chạy so sánh đối đầu giữa 3 thuật toán: Random Forest, Least Connection và Round Robin."""
        algos = ["RANDOM_FOREST", "LEAST_CONNECTION", "ROUND_ROBIN"]
        comparison_results = {}
        
        for algo in algos:
            res = self.run_simulation(count=req_count_per_algo, method=algo)
            
            # Tính chỉ số CPU cluster thực tế sau khi chạy thuật toán
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT AVG(cpu_usage) as avg_cpu FROM servers WHERE status = 'ONLINE'")
            row = cursor.fetchone()
            avg_cpu = float(row['avg_cpu']) if row and row['avg_cpu'] else 0.0
            conn.close()
            
            res['avg_cpu_utilization'] = avg_cpu
            comparison_results[algo] = res

        return comparison_results
