import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.health_services import health_monitor
from app.routes.routers import router


app = FastAPI(
    title="Marketing Intelligence API",
    description="API for managing ad campaigns and computing marketing KPIs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for tracking request times


@app.middleware("http")
async def track_requests(request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        health_monitor.record_request(duration_ms, is_error=False)
        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        health_monitor.record_request(duration_ms, is_error=True)
        raise e

app.include_router(router)
