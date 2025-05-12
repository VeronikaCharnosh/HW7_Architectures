# HW7_Architectures

# Logging, Alerts, and Resource Allocation

A cloud-native FastAPI + Celery application that demonstrates asynchronous processing, centralized logging to InfluxDB, and a simple alert engine that writes suspicious payloads to text reports. All services are containerized and orchestrated via Podman (or Docker) Compose.

## Project Structure

```
HW_7/
├── web_app/
│   ├── main.py             
│   ├── celery_app.py      
│   ├── tasks.py            
│   ├── requirements.txt    
│   └── Dockerfile         
├── logger_alert_engine/
│   ├── monitor.py          
│   ├── requirements.txt    
│   └── Dockerfile          
├── docker-compose.yml      
└── README.md              
```

## Features

* **Asynchronous Task Processing**
  Uses Celery + Redis to offload incoming JSON payloads from FastAPI into background tasks.

* **Centralized Logging**
  Every incoming request is logged to InfluxDB (measurement `interactions`) with timestamp, source, and raw payload.

* **Alert Engine**
  Detects PII or keywords (e.g. `"ssn"`) in the payload and writes a `.txt` report into `logger_alert_engine/error_reports/`.

* **Podman / Docker Compose**
  Single command to spin up all services: FastAPI app, Celery worker, Redis broker, InfluxDB, and the alert engine.

## Prerequisites

* Podman (or Docker)
* `podman-compose` 
* Local ports **6379**, **8086**, **8001**, and **5001** free.

## Quick Start

1. **Build & start all services**
   From project root (where `docker-compose.yml` lives):

   ```bash
   podman-compose build
   podman-compose up -d
   ```

2. **Verify services are running**

   ```bash
   podman ps
   ```


## How to Use

### 1. Submit Data to FastAPI

Send a JSON payload to the FastAPI endpoint:

```bash
curl -X POST http://localhost:8001/submit \
     -H "Content-Type: application/json" \
     -d '{"data":"hello"}'
```

**Response**

```json
{"message":"Task received and is being processed"}
```

### 2. Check InfluxDB Logs

1. Exec into InfluxDB container:

   ```bash
   podman exec -it hw7_influxdb influx -database logs
   ```
2. Show recent entries:

   ```sql
   SHOW MEASUREMENTS;
   SELECT * FROM interactions ORDER BY time DESC LIMIT 5;
   ```

### 3. Trigger an Alert

Include the substring `"ssn"` (or other configured keywords) in your payload:

```bash
curl -X POST http://localhost:8001/submit \
     -H "Content-Type: application/json" \
     -d '{"data":"my ssn is 123-45-6789"}'
```

After a few seconds, a file named like

```
alert_2025-05-12T14-30-05.123456.txt
```

will appear under

```
logger_alert_engine/error_reports/
```

and contain the timestamp, event type (`PII`), and the original payload.

### 4. Flood the Worker

Send 10 concurrent requests to test parallelism:

```bash
for i in {1..10}; do
  curl -s -X POST http://localhost:8001/submit \
       -H "Content-Type: application/json" \
       -d "{\"data\":\"task $i\"}" &
done
wait

podman logs hw7_worker | grep "received" | wc -l
```

You should see `10`, confirming Celery handled them all.

## Task 3: System Architecture

Below is an overview of our system’s architecture, its components, their responsibilities, and how they interact.

### Components

1. **FastAPI Web Application**

   * **Endpoints:**

     * `POST /submit` → accepts `{ data }`, validates, returns confirmation, and enqueues Celery task.
     * `GET /status/{task_id}` → returns task state & result.
   * **Alert Logic:**

     * Detects invalid input or PII synchronously, responds 400, and posts to Alert Engine.

2. **Celery Workers**

   * **Broker & Backend:** Redis
   * **Task:** `log_interaction(data)` logs to InfluxDB with fields: time, source, payload.

3. **Alert Engine (Flask)**

   * **Endpoint:** `POST /alert` → writes `alert_<timestamp>.txt` in `error_reports/`.

4. **InfluxDB**

   * **DB:** `logs`, **Measurement:** `interactions`
   * Stores time-series logs of all interactions.

5. **Redis**

   * Serves as Celery broker and result backend.

6. **Docker Compose**

   * Defines all five services on network `hw7-net`.

### Data Flow

```text
[Client]
   │ POST /submit
   ▼
[FastAPI]
   ├─ Validate & alert → Alert Engine
   ├─ Enqueue log_interaction → Redis broker
   └─ Return task_id

[Redis broker] → [Celery Worker]
   └─ log_interaction → InfluxDB

Client polls GET /status → FastAPI reads from Redis backend → returns status
```

### Sync vs. Async Operations

| Operation                               | Mode  | Component           |
| --------------------------------------- | ----- | ------------------- |
| Receive HTTP request & basic validation | Sync  | FastAPI             |
| Generate alert on invalid/PII input     | Sync  | FastAPI → Alert Eng |
| Enqueue background job                  | Sync  | FastAPI → Redis     |
| Write interaction log to InfluxDB       | Async | Celery Worker       |
| Fetch task status                       | Sync  | FastAPI (Redis)     |

## Task 4: Resource Scaling Estimation

| Concurrent Users | FastAPI Instances       | Celery Workers       | Redis & InfluxDB                           |
| ---------------- | ----------------------- | -------------------- | ------------------------------------------ |
| **10**           | 1 instance (512 MB RAM) | 2 workers (1 GB RAM) | Single Redis & InfluxDB nodes              |
| **50**           | 2–3 instances behind LB | 3–5 workers (2–3 GB) | Redis Sentinel (2 nodes), InfluxDB replica |
| **100+**         | 5+ instances (k8s)      | 6–8 workers (4–6 GB) | Redis Cluster (3+ nodes), InfluxDB cluster |

## Stop & Cleanup

```bash
podman-compose down --volumes
podman network rm hw7-net  # if needed
```

