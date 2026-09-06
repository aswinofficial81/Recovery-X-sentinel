from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.database import engine
from backend.app.routes.revenue_leaks import router as revenue_leaks_router
from backend.app.routes.dashboard import router as dashboard_router
from backend.app.routes.recovery import router as recovery_router
from backend.app.routes.audit_logs import router as audit_logs_router
from backend.app.routes.analytics import router as analytics_router
from backend.app.routes.merchants import router as merchants_router

app = FastAPI(
    title="Revenue AutoPilot API",
    description="Revenue leak detection and recovery backend",
    version="1.0.0"
)

app.include_router(revenue_leaks_router)
app.include_router(dashboard_router)
app.include_router(recovery_router)
app.include_router(audit_logs_router)
app.include_router(analytics_router)
app.include_router(merchants_router)

import os

# Dynamic CORS configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]
if cors_origins_env:
    for o in cors_origins_env.split(","):
        cleaned = o.strip()
        if cleaned and cleaned not in allowed_origins:
            allowed_origins.append(cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "Revenue AutoPilot API is running"
    }


@app.get("/health")
def health_check():

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:

        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=False)