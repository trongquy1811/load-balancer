import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from database.db import get_db_connection, init_db
from services.monitoring import CloudMonitoring
from services.load_balancer import LoadBalancerService
from models.random_forest import RandomForestModelManager
from services.auto_scaler import AutoScalerService
from utils.logger import logger

# Khởi tạo bảng dữ liệu khi ứng dụng FastAPI bật
init_db()

app = FastAPI(
    title="Cloud Resource Allocator & Load Balancer REST API",
    description="Hệ thống REST API điều khiển hạ tầng Đám mây, dự đoán Cân bằng tải AI (Random Forest), Tự động Co giãn và Truy vấn Nhật ký.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ------------------------------------------------------------------------------
# PYDANTIC SCHEMAS (Mô hình dữ liệu Request / Response)
# ------------------------------------------------------------------------------
class ServerSchema(BaseModel):
    id: str = Field(..., example="SRV-01", description="Mã nhận diện máy chủ ảo")
    name: str = Field(..., example="Application Server 1", description="Tên hiển thị máy chủ")
    cpu_usage: float = Field(..., example=45.0, description="Mức tiêu thụ CPU (%)")
    ram_usage: float = Field(..., example=50.0, description="Mức tiêu thụ RAM (%)")
    disk_usage: float = Field(..., example=30.0, description="Mức tiêu thụ Đĩa (%)")
    network_usage: float = Field(..., example=150.0, description="Lưu lượng mạng (Mbps)")
    queue_length: int = Field(..., example=3, description="Số lượng request trong hàng đợi")
    response_time: float = Field(..., example=120.0, description="Thời gian phản hồi (ms)")
    throughput: float = Field(..., example=450.0, description="Băng thông xử lý (req/s)")
    status: str = Field(..., example="ONLINE", description="Trạng thái (ONLINE, OFFLINE, MAINTENANCE)")
    timestamp: str = Field(..., example="2026-07-24T16:00:00", description="Thời gian cập nhật")

class ClusterMetricsSchema(BaseModel):
    server_count: int = Field(..., example=3, description="Tổng số máy chủ đang hoạt động")
    avg_cpu: float = Field(..., example=46.7, description="Mức tiêu thụ CPU trung bình (%)")
    avg_ram: float = Field(..., example=55.6, description="Mức tiêu thụ RAM trung bình (%)")
    avg_response_time: float = Field(..., example=166.7, description="Thời gian phản hồi trung bình (ms)")
    total_throughput: float = Field(..., example=1420.0, description="Tổng throughput toàn cụm")

class PredictRequestSchema(BaseModel):
    cpu_usage: float = Field(45.0, description="Tải CPU cần thiết (%)", ge=0.0, le=100.0)
    ram_usage: float = Field(50.0, description="Tải RAM cần thiết (%)", ge=0.0, le=100.0)
    disk_usage: float = Field(30.0, description="Tải Disk (%)", ge=0.0, le=100.0)
    network_usage: float = Field(150.0, description="Tải Network (Mbps)", ge=0.0)
    queue_length: int = Field(5, description="Độ dài hàng đợi hiện tại", ge=0)
    response_time: float = Field(120.0, description="Thời gian phản hồi dự kiến (ms)", ge=0.0)
    throughput: float = Field(450.0, description="Throughput xử lý dự kiến (req/s)", ge=0.0)

class PredictResponseSchema(BaseModel):
    predicted_server: str = Field(..., example="SRV-01", description="Máy chủ được mô hình AI chỉ định")
    confidence_score: float = Field(..., example=0.92, description="Độ tin cậy của thuật toán Random Forest (0 - 1)")
    algorithm_used: str = Field(..., example="RANDOM_FOREST", description="Thuật toán được áp dụng")

class CreateRequestSchema(PredictRequestSchema):
    method: Optional[str] = Field(None, example="RANDOM_FOREST", description="Tùy chọn thuật toán (RANDOM_FOREST, LEAST_CONNECTION, ROUND_ROBIN)")

class CreateRequestResponseSchema(BaseModel):
    request_id: str = Field(..., example="REQ-A1B2C3D4", description="Mã định danh yêu cầu")
    allocated_server: str = Field(..., example="SRV-01", description="Máy chủ nhận xử lý")
    routing_method: str = Field(..., example="RANDOM_FOREST", description="Thuật toán đã áp dụng")
    confidence_score: float = Field(..., example=0.95, description="Độ tin cậy")
    status: str = Field(..., example="PROCESSED", description="Trạng thái xử lý")

class TrainResponseSchema(BaseModel):
    status: str = Field(..., example="SUCCESS", description="Trạng thái huấn luyện")
    accuracy: float = Field(..., example=0.985, description="Độ chính xác trên tập kiểm thử")
    precision: float = Field(..., example=0.981, description="Chỉ số Precision")
    recall: float = Field(..., example=0.985, description="Chỉ số Recall")
    f1_score: float = Field(..., example=0.983, description="Chỉ số F1 Score")
    feature_importances: Dict[str, float] = Field(..., description="Độ quan trọng của từng thuộc tính")

# ------------------------------------------------------------------------------
# ENDPOINTS REST API
# ------------------------------------------------------------------------------
@app.get("/servers", response_model=List[ServerSchema], summary="Trích xuất danh sách tất cả các máy chủ ảo", tags=["Servers"])
def get_servers():
    """Trả về danh sách toàn bộ các Virtual Server Nodes trong hạ tầng đám mây."""
    monitoring = CloudMonitoring()
    servers = monitoring.collect_realtime_metrics()
    return servers

@app.get("/metrics", response_model=ClusterMetricsSchema, summary="Trích xuất chỉ số tổng quan toàn cụm máy chủ", tags=["Metrics"])
def get_metrics():
    """Trả về chỉ số KPI tổng hợp của Cluster bao gồm CPU, RAM, Response Time, Throughput."""
    monitoring = CloudMonitoring()
    summary = monitoring.get_cluster_summary()
    return summary

@app.post("/predict", response_model=PredictResponseSchema, summary="Dự đoán máy chủ tối ưu bằng Random Forest AI", tags=["Load Balancer"])
def predict_best_server(req_data: PredictRequestSchema):
    """Sử dụng mô hình Random Forest Classifier để chọn máy chủ phù hợp nhất cho request mà không ghi nhận vào DB."""
    rf_manager = RandomForestModelManager()
    features = [
        req_data.cpu_usage, req_data.ram_usage, req_data.disk_usage,
        req_data.network_usage, req_data.queue_length, req_data.response_time,
        req_data.throughput
    ]
    try:
        server_id, confidence = rf_manager.predict(features)
        return {
            "predicted_server": server_id,
            "confidence_score": confidence,
            "algorithm_used": "RANDOM_FOREST"
        }
    except Exception as e:
        logger.error(f"Lỗi endpoint /predict: {e}")
        raise HTTPException(status_code=500, detail=f"Dự đoán mô hình AI thất bại: {str(e)}")

@app.post("/requests", response_model=CreateRequestResponseSchema, status_code=status.HTTP_201_CREATED, summary="Khởi tạo và định tuyến client request vào hệ thống", tags=["Load Balancer"])
def create_request(req_data: CreateRequestSchema):
    """Định tuyến 1 client request vào hạ tầng Đám mây, cập nhật tải máy chủ và lưu vết vào SQLite."""
    lb_service = LoadBalancerService()
    req_dict = req_data.dict()
    
    target_node, method_used, score = lb_service.route_request(req_dict, method=req_data.method)
    if not target_node:
        raise HTTPException(status_code=503, detail="Không có máy chủ ONLINE nào khả dụng!")
        
    req_id = lb_service.log_and_execute_request(target_node, method_used, score, req_dict)
    
    return {
        "request_id": req_id,
        "allocated_server": target_node,
        "routing_method": method_used,
        "confidence_score": score,
        "status": "PROCESSED"
    }

@app.post("/train", response_model=TrainResponseSchema, summary="Huấn luyện lại mô hình AI Random Forest", tags=["Machine Learning"])
def train_model():
    """Kích hoạt quy trình sinh dữ liệu tổng hợp và tái huấn luyện mô hình Machine Learning."""
    rf_manager = RandomForestModelManager()
    try:
        metrics = rf_manager.train_and_save()
        return {
            "status": "SUCCESS",
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1_score": metrics["f1_score"],
            "feature_importances": metrics["feature_importances"]
        }
    except Exception as e:
        logger.error(f"Lỗi endpoint /train: {e}")
        raise HTTPException(status_code=500, detail=f"Huấn luyện mô hình thất bại: {str(e)}")

@app.get("/history", summary="Tra cứu lịch sử nhật ký định tuyến requests", tags=["Logs"])
def get_request_history(
    limit: int = Query(100, ge=1, le=1000, description="Số bản ghi tối đa"),
    method: Optional[str] = Query(None, description="Lọc theo thuật toán (RANDOM_FOREST, LEAST_CONNECTION, ROUND_ROBIN)")
):
    """Truy vấn danh sách lịch sử định tuyến yêu cầu trong cơ sở dữ liệu SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if method:
        cursor.execute("SELECT * FROM requests_log WHERE routing_method = ? ORDER BY timestamp DESC LIMIT ?", (method, limit))
    else:
        cursor.execute("SELECT * FROM requests_log ORDER BY timestamp DESC LIMIT ?", (limit,))
        
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
