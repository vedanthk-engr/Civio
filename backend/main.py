from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from backend.routers import (
    issues,
    agent,
    intelligence,
    authority,
    gamification,
    pulse_scan,
    transparency,
    whatsapp,
    ngo
)

app = FastAPI(
    title="Civio — Agentic Civic Intelligence Platform API",
    description="FastAPI Backend for Civio (CivicSentinel)",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Next.js domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(issues.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(intelligence.router, prefix="/api")
app.include_router(authority.router, prefix="/api")
app.include_router(gamification.router, prefix="/api")
app.include_router(pulse_scan.router, prefix="/api")
app.include_router(transparency.router, prefix="/api")
app.include_router(whatsapp.router, prefix="/api")
app.include_router(ngo.router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Civio API Gateway",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # Allow port overrides via env
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
