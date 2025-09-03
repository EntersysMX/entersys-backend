from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Entersys Backend API",
    description="Backend API for Entersys.mx project",
    version="1.0.0"
)

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str

@app.get("/")
def read_root():
    return {"message": "Entersys Backend API"}

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy", 
        message="Entersys Backend API is running",
        version="1.0.0"
    )

@app.get("/api/v1/status")
def api_status():
    return {
        "api_version": "v1",
        "status": "operational",
        "services": {
            "database": "connected",
            "cache": "operational"
        }
    }