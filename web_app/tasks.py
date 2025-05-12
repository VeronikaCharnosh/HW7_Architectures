import datetime
import requests
from celery import Celery
from influxdb import InfluxDBClient

celery = Celery(
    'web_app',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/1',
)
# щоб таски знайшлися
import tasks  # noqa

@celery.task
def log_interaction(data):
    # 1) Лог у InfluxDB
    client = InfluxDBClient(host='influxdb', port=8086, database='logs')
    point = {
        "measurement": "interactions",
        "tags": {"source": "web_app"},
        "time": datetime.datetime.utcnow().isoformat(),
        "fields": {"payload": str(data)},
    }
    client.write_points([point])

    # 2) Alert, якщо бачили PII
    if any(s in str(data).lower() for s in ("ssn", "password")):
        alert = {
            "time": point["time"],
            "event": "PII",
            "description": str(data)
        }
        # надсилаємо на логер
        requests.post("http://logger:5001/alert", json=alert)
