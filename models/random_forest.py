import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
from config import Config
from database.db import get_db_connection
from utils.logger import logger

class RandomForestModelManager:
    """Quản lý huấn luyện, lưu trữ và dự đoán của mô hình Random Forest Classifier."""
    
    def __init__(self):
        self.model_path = Config.MODEL_PATH
        self.clf = RandomForestClassifier(n_estimators=100, criterion='gini', random_state=42)

    def generate_synthetic_train_data(self):
        """Sinh dữ liệu huấn luyện mẫu phù hợp với trạng thái hạ tầng thực tế."""
        np.random.seed(42)
        records = 800
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM servers WHERE status = 'ONLINE'")
        rows = cursor.fetchall()
        server_ids = [r['id'] for r in rows]
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
        
        # Gán nhãn server tốt nhất dựa trên tải trọng
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
        logger.info(f"Đã tạo dữ liệu huấn luyện tổng hợp {records} bản ghi tại {Config.TRAIN_DATA_PATH}")

    def train_and_save(self) -> Dict[str, Any]:
        """Huấn luyện lại mô hình RF và tính toán đầy đủ các chỉ số đánh giá ML."""
        if not os.path.exists(Config.TRAIN_DATA_PATH):
            self.generate_synthetic_train_data()
            
        df = pd.read_csv(Config.TRAIN_DATA_PATH)
        feature_cols = ['cpu_usage', 'ram_usage', 'disk_usage', 'network_usage', 'queue_length', 'response_time', 'throughput']
        X = df[feature_cols]
        y = df['best_server']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.clf.fit(X_train, y_train)
        preds = self.clf.predict(X_test)
        
        # Đánh giá chỉ số ML chi tiết
        acc = float(accuracy_score(y_test, preds))
        prec = float(precision_score(y_test, preds, average='weighted', zero_division=0))
        rec = float(recall_score(y_test, preds, average='weighted', zero_division=0))
        f1 = float(f1_score(y_test, preds, average='weighted', zero_division=0))
        cm = confusion_matrix(y_test, preds).tolist()
        class_report = classification_report(y_test, preds, output_dict=True, zero_division=0)
        
        feature_importances = dict(zip(X.columns, [float(v) for v in self.clf.feature_importances_]))
        
        metrics = {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "confusion_matrix": cm,
            "feature_importances": feature_importances,
            "classification_report": class_report,
            "classes": self.clf.classes_.tolist()
        }
        
        joblib.dump(self.clf, self.model_path)
        logger.info(f"Huấn luyện thành công mô hình Random Forest. Accuracy={acc:.4f}, F1={f1:.4f}")
        return metrics

    def load_model(self) -> RandomForestClassifier:
        """Tải mô hình đã được huấn luyện từ tập tin pickle."""
        if not os.path.exists(self.model_path):
            self.train_and_save()
        return joblib.load(self.model_path)

    def predict(self, features: list) -> Tuple[str, float]:
        """Dự đoán server tối ưu và độ tin cậy dựa trên tính chất request."""
        model = self.load_model()
        arr = np.array(features).reshape(1, -1)
        pred_server = model.predict(arr)[0]
        probabilities = model.predict_proba(arr)[0]
        confidence = float(np.max(probabilities))
        return str(pred_server), confidence
