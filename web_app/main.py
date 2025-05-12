from fastapi import FastAPI, HTTPException
from tasks import log_interaction

app = FastAPI()

@app.post("/submit")
async def submit(data: dict):
    # простенька валідація
    if "data" not in data:
        raise HTTPException(400, detail="Field 'data' is required")
    # шлемо в Celery, task виконається асинхронно
    log_interaction.delay(data)
    return {"message": "Task received and is being processed"}

