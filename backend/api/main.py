from fastapi import FastAPI

from .routers import tasks

app = FastAPI(
    title="Task Management API",
    version="0.1.0",
)

app.include_router(tasks.router, prefix="/api")
