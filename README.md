# Cloud Resource Management using Random Forest

## Overview

Cloud Resource Management using Random Forest is a simulation-based cloud load balancing system developed with **Python**, **Streamlit**, **SQLite**, and **Scikit-learn**.

The project applies a **Random Forest Machine Learning model** to predict the most suitable server for incoming client requests based on real-time server metrics. To improve reliability, the system also includes fallback load balancing algorithms such as **Least Connection** and **Round Robin**.

The application provides a web dashboard for monitoring server resources, training the machine learning model, simulating request routing, and viewing request logs.

---

## Features

- Real-time cloud infrastructure monitoring
- Intelligent load balancing using Random Forest
- Automatic model training and prediction
- Least Connection fallback strategy
- Round Robin fallback strategy
- SQLite database for server and request management
- Auto Scaling simulation based on CPU utilization
- Interactive dashboard with Streamlit and Plotly
- Request logging and performance statistics

---

## System Architecture

```
                Client Request
                      │
                      ▼
          Resource Information Collection
      (CPU, RAM, Network, Queue, Response Time)
                      │
                      ▼
          Random Forest Prediction Model
                      │
        ┌─────────────┴─────────────┐
        │                           │
 Prediction Success          Prediction Failed
        │                           │
        ▼                           ▼
 Select Best Server         Least Connection
                                    │
                                    ▼
                               Round Robin
                                    │
                                    ▼
                           Request Logging
                                    │
                                    ▼
                              Dashboard
```

---

## Technologies Used

- Python 3.11
- Streamlit
- Scikit-learn
- Random Forest Classifier
- Pandas
- NumPy
- Plotly
- SQLite
- Joblib

---

## Project Structure

```
load-balancer/
│
├── app.py
├── requirements.txt
├── README.md
│
├── data/
│   └── train_data.csv
│
├── database/
│   └── cloud.db
│
├── model/
│   └── random_forest.pkl
│
└── assets/
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/trongquy1811/load-balancer.git
cd load-balancer
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the environment:

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
streamlit run app.py
```

The application will be available at:

```
http://localhost:8501
```

---

## Machine Learning Model

The system uses a **Random Forest Classifier** to predict the optimal server for handling incoming requests.

### Input Features

- CPU Usage
- RAM Usage
- Disk Usage
- Network Usage
- Queue Length
- Response Time
- Throughput

### Output

- Selected Server ID
- Prediction Confidence

---

## Load Balancing Strategy

Priority order:

1. Random Forest Prediction
2. Least Connection
3. Round Robin

This multi-layer approach ensures high availability even if the machine learning model cannot make a prediction.

---

## Dashboard

The Streamlit dashboard provides:

- Server status monitoring
- CPU and RAM visualization
- Request statistics
- Auto Scaling status
- Machine learning training interface
- Request history

---

## Database

SQLite stores:

- User accounts
- Server information
- Request logs

---

## Future Improvements

- Replace simulated data with real cloud metrics
- Deploy on AWS or Azure
- Integrate Docker and Kubernetes
- Add REST API using FastAPI
- Support Reinforcement Learning for adaptive load balancing
- Real-time monitoring with Prometheus and Grafana

---

## Author

**Nguyen Trong Quy**

Bachelor of Information Technology

University of Science

---

## License

This project is intended for educational and research purposes.