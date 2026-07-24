import time
import random
import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import Config
from database.db import get_db_connection, init_db
from services.auth import AuthManager
from services.monitoring import CloudMonitoring
from services.load_balancer import LoadBalancerService
from services.auto_scaler import AutoScalerService
from services.simulator import LoadTestingSimulator
from models.random_forest import RandomForestModelManager
from utils.logger import logger

# Khởi tạo bảng dữ liệu SQLite
init_db()

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Cloud Resource Management & Load Balancer",
    layout="wide",
    page_icon="☁️",
    initial_sidebar_state="expanded"
)

# Custom CSS giao diện hiện đại Glassmorphic
st.markdown("""
<style>
    .metric-container {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .status-online { color: #10b981; font-weight: bold; }
    .status-offline { color: #ef4444; font-weight: bold; }
    .status-maint { color: #f59e0b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo trạng thái phiên làm việc (Session State)
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = True
    st.session_state["username"] = "admin"
    st.session_state["role"] = "Admin"

# Thanh Sidebar Điều hướng chính
st.sidebar.title("☁️ Cloud Manager & ML Balancer")
st.sidebar.caption("Hệ thống Giám sát, Cân bằng Tải AI & Co giãn Hạ tầng")
st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Tài khoản:** `{st.session_state['username']}`")
st.sidebar.write(f"🛡️ **Quyền hạn:** `{st.session_state['role']}`")
st.sidebar.markdown("---")

menu = st.sidebar.radio("📋 Menu Chức Năng", [
    "Dashboard Giám sát Tải",
    "Quản lý Server Nodes",
    "Mô phỏng Load Testing",
    "Performance Comparison",
    "Auto Scaling Visualization",
    "Đánh giá Mô hình AI (ML)",
    "Lịch sử Request History",
    "Cấu hình Hệ thống"
])

monitoring = CloudMonitoring()
lb_service = LoadBalancerService()
rf_manager = RandomForestModelManager()
simulator = LoadTestingSimulator()

# ==============================================================================
# 1. REAL-TIME DASHBOARD (Giám sát chỉ số thời gian thực)
# ==============================================================================
if menu == "Dashboard Giám sát Tải":
    st.title("📊 Real-time Cloud Infrastructure Dashboard")
    st.caption("Cập nhật tự động các chỉ số hạ tầng đám mây: CPU, RAM, Disk, Network, Throughput, Response Time, Active Requests.")
    
    col_refresh1, col_refresh2 = st.columns([1, 4])
    with col_refresh1:
        auto_refresh = st.checkbox("🔄 Auto-Refresh (3s)", value=False)
    with col_refresh2:
        if st.button("⚡ làm mới ngay"):
            st.rerun()

    metrics = monitoring.collect_realtime_metrics()
    df_servers = pd.DataFrame(metrics)
    summary = monitoring.get_cluster_summary()

    # Thẻ KPI chính
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Node Hoạt Động", f"{summary['server_count']} Nodes")
    kpi2.metric("CPU Cluster TB", f"{summary['avg_cpu']:.1f}%")
    kpi3.metric("RAM Cluster TB", f"{summary['avg_ram']:.1f}%")
    kpi4.metric("Thời Gian Phản Hồi", f"{summary['avg_response_time']:.1f} ms")
    kpi5.metric("Tổng Throughput", f"{summary['total_throughput']:.1f} req/s")

    st.markdown("---")
    st.subheader("🖥️ Trạng thái Chi tiết các Máy Chủ Áo (Virtual Server Nodes)")

    if not df_servers.empty:
        st.dataframe(
            df_servers[['id', 'name', 'status', 'cpu_usage', 'ram_usage', 'disk_usage', 'network_usage', 'queue_length', 'response_time', 'throughput', 'timestamp']],
            use_container_width=True,
            column_config={
                "cpu_usage": st.column_config.ProgressColumn("CPU (%)", format="%.1f%%", min_value=0, max_value=100),
                "ram_usage": st.column_config.ProgressColumn("RAM (%)", format="%.1f%%", min_value=0, max_value=100),
                "disk_usage": st.column_config.ProgressColumn("Disk (%)", format="%.1f%%", min_value=0, max_value=100),
                "response_time": st.column_config.NumberColumn("Response Time (ms)", format="%.1f ms"),
                "throughput": st.column_config.NumberColumn("Throughput (req/s)", format="%.1f")
            }
        )

        st.markdown("### 📈 Biểu đồ Tiêu thụ Tài nguyên Cluster")
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            fig_cpu = px.bar(df_servers, x='id', y='cpu_usage', color='cpu_usage', title='Mức Tiêu Thụ CPU (%)', color_continuous_scale='Reds')
            fig_cpu.update_layout(template="plotly_dark")
            st.plotly_chart(fig_cpu, use_container_width=True)

        with c_chart2:
            fig_ram = px.bar(df_servers, x='id', y='ram_usage', color='ram_usage', title='Mức Tiêu Thụ RAM (%)', color_continuous_scale='Blues')
            fig_ram.update_layout(template="plotly_dark")
            st.plotly_chart(fig_ram, use_container_width=True)

    # Kiểm tra Auto-Scaling
    scale_summary, scale_events = AutoScalerService.check_and_scale(summary['avg_cpu'])
    for ev in scale_events:
        if ev['type'] == 'SCALE_UP':
            st.warning(f"🚨 {ev['message']}")
        elif ev['type'] == 'SCALE_DOWN':
            st.info(f"♻️ {ev['message']}")

    if auto_refresh:
        time.sleep(3)
        st.rerun()

# ==============================================================================
# 2. SERVER MANAGEMENT (Quản lý các Node máy chủ)
# ==============================================================================
elif menu == "Quản lý Server Nodes":
    st.title("🖥️ Quản lý Máy chủ Áo (Server Nodes Management)")
    st.write("Thêm mới, xóa máy chủ hoặc cập nhật trạng thái hoạt động (`ONLINE`, `OFFLINE`, `MAINTENANCE`).")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Form Thêm Server Mới
    with st.expander("➕ Thêm Máy Chủ Áo Mới", expanded=False):
        with st.form("add_server_form"):
            new_id = st.text_input("Mã Server ID", value=f"SRV-{random.randint(10,99)}")
            new_name = st.text_input("Tên Server", value="Application Server Custom")
            status_opt = st.selectbox("Trạng thái", ["ONLINE", "OFFLINE", "MAINTENANCE"])
            submitted = st.form_submit_button("Thêm Máy Chủ")
            
            if submitted:
                try:
                    now_str = datetime.datetime.now().isoformat()
                    cursor.execute("""
                        INSERT INTO servers VALUES (?, ?, 30.0, 40.0, 25.0, 100.0, 0, 50.0, 200.0, ?, ?)
                    """, (new_id, new_name, status_opt, now_str))
                    conn.commit()
                    st.success(f"Đã thêm máy chủ mới: {new_id} ({new_name})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Không thể thêm máy chủ: {e}")

    cursor.execute("SELECT * FROM servers")
    servers_db = cursor.fetchall()
    conn.close()

    st.subheader("📋 Danh Sách Máy Chủ Hiện Tại")
    for s in servers_db:
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns([2, 3, 2, 2, 2])
        with col_s1:
            st.write(f"**{s['id']}**")
        with col_s2:
            st.write(s['name'])
        with col_s3:
            if s['status'] == 'ONLINE':
                st.markdown("<span class='status-online'>🟢 ONLINE</span>", unsafe_allow_html=True)
            elif s['status'] == 'OFFLINE':
                st.markdown("<span class='status-offline'>🔴 OFFLINE</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='status-maint'>🟡 MAINTENANCE</span>", unsafe_allow_html=True)
        with col_s4:
            new_st = st.selectbox("Đổi trạng thái", ["ONLINE", "OFFLINE", "MAINTENANCE"], index=["ONLINE", "OFFLINE", "MAINTENANCE"].index(s['status']), key=f"sel_{s['id']}")
            if new_st != s['status']:
                conn_u = get_db_connection()
                conn_u.execute("UPDATE servers SET status = ? WHERE id = ?", (new_st, s['id']))
                conn_u.commit()
                conn_u.close()
                st.success(f"Đã đổi {s['id']} sang {new_st}")
                st.rerun()
        with col_s5:
            if st.button("🗑️ Xóa Node", key=f"del_{s['id']}"):
                conn_d = get_db_connection()
                conn_d.execute("DELETE FROM servers WHERE id = ?", (s['id'],))
                conn_d.commit()
                conn_d.close()
                st.success(f"Đã xóa {s['id']}")
                st.rerun()

# ==============================================================================
# 3. LOAD TESTING SIMULATOR (Mô phỏng tải song song)
# ==============================================================================
elif menu == "Mô phỏng Load Testing":
    st.title("🚀 Load Test Simulation")
    st.write("Sinh luồng client requests đồng thời (10, 100, 500, 1000 requests) đi qua Load Balancer, cập nhật tài nguyên server và ghi nhật ký vào SQLite.")

    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    run_10 = col_btn1.button("🔥 Generate 10 Requests", use_container_width=True)
    run_100 = col_btn2.button("🚀 Generate 100 Requests", use_container_width=True)
    run_500 = col_btn3.button("⚡ Generate 500 Requests", use_container_width=True)
    run_1000 = col_btn4.button("💥 Generate 1000 Requests", use_container_width=True)

    target_count = 0
    if run_10: target_count = 10
    elif run_100: target_count = 100
    elif run_500: target_count = 500
    elif run_1000: target_count = 1000

    if target_count > 0:
        st.markdown(f"### ⚙️ Đang thực thi Load Test với **{target_count} Requests**...")
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_progress(ratio):
            progress_bar.progress(ratio)
            status_text.text(f"Tiến độ: {ratio*100:.1f}%")

        sim_res = simulator.run_simulation(count=target_count, progress_callback=update_progress)

        st.success(f"🎉 Hoàn thành Load Test {target_count} requests trong {sim_res['total_time_seconds']:.2f} giây!")
        
        c_r1, c_r2, c_r3, c_r4 = st.columns(4)
        c_r1.metric("Requests Thành Công", f"{sim_res['successful_requests']} / {target_count}")
        c_r2.metric("Tỷ Lệ Thành Công", f"{sim_res['success_rate']:.1f}%")
        c_r3.metric("Response Time TB", f"{sim_res['avg_response_time']:.1f} ms")
        c_r4.metric("Throughput Đạt Được", f"{sim_res['throughput_req_per_sec']:.1f} req/s")

        st.markdown("### 📊 Phân phối Tải trọng giữa các Nodes (Load Distribution)")
        df_dist = pd.DataFrame(list(sim_res['load_distribution'].items()), columns=['Server Node', 'Số Requests Đã Nhận'])
        fig_dist = px.pie(df_dist, values='Số Requests Đã Nhận', names='Server Node', title='Tỷ lệ Phân bổ Tải trọng theo Node')
        fig_dist.update_layout(template="plotly_dark")
        st.plotly_chart(fig_dist, use_container_width=True)

# ==============================================================================
# 4. PERFORMANCE COMPARISON (So sánh hiệu năng 3 thuật toán)
# ==============================================================================
elif menu == "Performance Comparison":
    st.title("⚖️ Performance Comparison Page")
    st.write("So sánh đối đầu trực tiếp giữa 3 thuật toán: **Random Forest AI**, **Round Robin** và **Least Connection**.")

    col_comp_ctrl1, col_comp_ctrl2 = st.columns([3, 1])
    with col_comp_ctrl1:
        test_size = st.slider("Số lượng requests kiểm thử cho mỗi thuật toán", 20, 500, 100)
    with col_comp_ctrl2:
        btn_start_comp = st.button("🏋️ Chạy So Sánh Đối Đầu", use_container_width=True)

    if btn_start_comp:
        with st.spinner("Đang chạy mô phỏng đo đạc hiệu năng cả 3 thuật toán..."):
            comp_data = simulator.compare_algorithms(req_count_per_algo=test_size)
            
            # Chuẩn bị dữ liệu bảng
            rows = []
            for algo, res in comp_data.items():
                rows.append({
                    "Algorithm": algo,
                    "Avg Response Time (ms)": res["avg_response_time"],
                    "Throughput (req/s)": res["throughput_req_per_sec"],
                    "CPU Utilization (%)": res["avg_cpu_utilization"],
                    "Success Rate (%)": res["success_rate"]
                })
            df_comp = pd.DataFrame(rows)
            st.dataframe(df_comp, use_container_width=True)

            st.markdown("### 📊 Biểu đồ So sánh Trực quan")
            c_comp1, c_comp2 = st.columns(2)
            with c_comp1:
                fig_rt = px.bar(df_comp, x='Algorithm', y='Avg Response Time (ms)', color='Algorithm', title='Thời Gian Phản Hồi Thấp Nhất (Tối Ưu)')
                fig_rt.update_layout(template="plotly_dark")
                st.plotly_chart(fig_rt, use_container_width=True)

            with c_comp2:
                fig_tp = px.bar(df_comp, x='Algorithm', y='Throughput (req/s)', color='Algorithm', title='Throughput Xử Lý Cao Nhất')
                fig_tp.update_layout(template="plotly_dark")
                st.plotly_chart(fig_tp, use_container_width=True)

# ==============================================================================
# 5. AUTO SCALING VISUALIZATION (Trực quan hóa Co giãn Hạ tầng)
# ==============================================================================
elif menu == "Auto Scaling Visualization":
    st.title("📈 Auto Scaling Visualization")
    st.write("Trực quan hóa quá trình Tự động Cấp phát Node mới (CPU > 80%) và Giải phóng Node nhàn rỗi (CPU < 20%).")

    summary = monitoring.get_cluster_summary()
    st.info(f"📊 **Cluster Trạng thái Hiện tại**: {summary['server_count']} Nodes ONLINE | CPU Cluster Trung Bình: **{summary['avg_cpu']:.1f}%**")

    # Hiển thị thẻ danh sách Cụm hiện tại
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, cpu_usage, status FROM servers WHERE status = 'ONLINE'")
    current_nodes = cursor.fetchall()
    conn.close()

    st.markdown("#### 🖥️ Danh Sách Node Trong Cluster Hiện Tại:")
    cols_nodes = st.columns(min(6, max(1, len(current_nodes))))
    for idx, node in enumerate(current_nodes):
        with cols_nodes[idx % len(cols_nodes)]:
            st.metric(node['id'], f"CPU: {node['cpu_usage']:.1f}%", delta="ONLINE")

    st.markdown("---")
    st.subheader("📜 Lịch sử Các Sự Kiện Co Giãn (Scaling Events Log)")
    history = AutoScalerService.get_scaling_history(limit=20)
    if history:
        df_hist = pd.DataFrame(history)
        st.dataframe(df_hist[['id', 'event_type', 'server_id', 'reason', 'cpu_avg', 'cluster_size', 'timestamp']], use_container_width=True)
        
        fig_scale = px.line(df_hist, x='timestamp', y='cluster_size', markers=True, title='Biến thiên Quy mô Cluster Size Theo Thời Gian')
        fig_scale.update_layout(template="plotly_dark")
        st.plotly_chart(fig_scale, use_container_width=True)
    else:
        st.info("Chưa có sự kiện co giãn nào được ghi nhận.")

# ==============================================================================
# 6. MACHINE LEARNING EVALUATION (Đánh giá chi tiết mô hình AI)
# ==============================================================================
elif menu == "Đánh giá Mô hình AI (ML)":
    st.title("🧠 Đánh giá Mô hình Machine Learning (Random Forest)")
    st.write("Hiển thị các chỉ số kiểm thử nâng cao: **Accuracy, Precision, Recall, F1 Score, Confusion Matrix, Classification Report, Feature Importances**.")

    if st.button("🏋️ Retrain & Re-Evaluate Model"):
        with st.spinner("Đang huấn luyện và tính toán chỉ số đánh giá..."):
            rf_manager.train_and_save()
            st.success("Đã hoàn tất huấn luyện lại mô hình!")

    try:
        metrics = rf_manager.train_and_save()
        c_ml1, c_ml2, c_ml3, c_ml4 = st.columns(4)
        c_ml1.metric("Accuracy Score", f"{metrics['accuracy']*100:.2f}%")
        c_ml2.metric("Precision (Weighted)", f"{metrics['precision']*100:.2f}%")
        c_ml3.metric("Recall (Weighted)", f"{metrics['recall']*100:.2f}%")
        c_ml4.metric("F1 Score (Weighted)", f"{metrics['f1_score']*100:.2f}%")

        st.markdown("---")
        c_eval1, c_eval2 = st.columns(2)
        with c_eval1:
            st.markdown("### 📊 Confusion Matrix Heatmap")
            cm = np.array(metrics['confusion_matrix'])
            fig_cm = px.imshow(cm, text_auto=True, color_continuous_scale='Blues', title='Confusion Matrix', labels=dict(x="Predicted Server", y="Actual Server"))
            fig_cm.update_layout(template="plotly_dark")
            st.plotly_chart(fig_cm, use_container_width=True)

        with c_eval2:
            st.markdown("### 🌟 Feature Importance Ranking")
            df_imp = pd.DataFrame(list(metrics['feature_importances'].items()), columns=['Thuộc tính', 'Độ quan trọng']).sort_values(by='Độ quan trọng', ascending=True)
            fig_imp = px.bar(df_imp, x='Độ quan trọng', y='Thuộc tính', orientation='h', color='Độ quan trọng', title='Feature Importance')
            fig_imp.update_layout(template="plotly_dark")
            st.plotly_chart(fig_imp, use_container_width=True)

        st.markdown("### 📋 Classification Report Chi tiết")
        st.json(metrics['classification_report'])
    except Exception as e:
        st.error(f"Chưa có dữ liệu đánh giá mô hình: {e}")

# ==============================================================================
# 7. REQUEST HISTORY (Lịch sử định tuyến)
# ==============================================================================
elif menu == "Lịch sử Request History":
    st.title("📜 Lịch sử Định tuyến Requests (Request History)")
    st.write("Bảng tra cứu lịch sử chi tiết tất cả các requests đã được gửi và xử lý bởi hệ thống Cân bằng tải.")

    conn = get_db_connection()
    df_logs = pd.read_sql_query("SELECT * FROM requests_log ORDER BY timestamp DESC", conn)
    conn.close()

    if not df_logs.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search_query = st.text_input("🔍 Tìm kiếm theo Request ID hoặc Server Node", "")
        with col_f2:
            method_filter = st.multiselect("Lọc theo Thuật toán Routing", df_logs['routing_method'].unique().tolist())

        filtered_df = df_logs.copy()
        if search_query:
            filtered_df = filtered_df[
                filtered_df['request_id'].str.contains(search_query, case=False, na=False) |
                filtered_df['allocated_server'].str.contains(search_query, case=False, na=False)
            ]
        if method_filter:
            filtered_df = filtered_df[filtered_df['routing_method'].isin(method_filter)]

        st.dataframe(filtered_df, use_container_width=True)

        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Tải xuống Nhật ký Lịch sử (CSV)",
            data=csv_data,
            file_name="cloud_request_history.csv",
            mime="text/csv"
        )
    else:
        st.info("Chưa có dữ liệu nhật ký request nào.")

# ==============================================================================
# 8. CẤU HÌNH HỆ THỐNG
# ==============================================================================
elif menu == "Cấu hình Hệ thống":
    st.title("⚙️ System Settings & Thresholds")
    st.write("Điều chỉnh cấu hình các ngưỡng tự động co giãn và thông số hệ thống.")

    with st.form("settings_form"):
        cpu_high = st.slider("Ngưỡng CPU Auto Scale Up (%)", 50.0, 95.0, Config.CPU_HIGH_THRESHOLD)
        cpu_low = st.slider("Ngưỡng CPU Auto Scale Down (%)", 5.0, 40.0, Config.CPU_LOW_THRESHOLD)
        max_servers = st.number_input("Số lượng Server tối đa", min_value=2, max_value=20, value=Config.MAX_SERVERS)
        min_servers = st.number_input("Số lượng Server tối thiểu", min_value=1, max_value=5, value=Config.MIN_SERVERS)
        
        save_btn = st.form_submit_button("Lưu Cấu Hình")
        if save_btn:
            Config.CPU_HIGH_THRESHOLD = cpu_high
            Config.CPU_LOW_THRESHOLD = cpu_low
            Config.MAX_SERVERS = max_servers
            Config.MIN_SERVERS = min_servers
            st.success("Đã cập nhật cấu hình hệ thống thành công!")