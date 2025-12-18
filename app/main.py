"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api import routes
from app.models.database import init_db

app = FastAPI(
    title="Goldilocks V2 PnL Tracker",
    description="Public dashboard for NBA PRA betting model performance",
    version="0.1.0"
)

# Include API routes
app.include_router(routes.router, prefix="/api", tags=["api"])

# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    """Serve the dashboard HTML."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Goldilocks V2 PnL Tracker API", "docs": "/docs"}


@app.get("/live")
async def live_page():
    """Serve the live tracking HTML."""
    live_path = static_dir / "live.html"
    if live_path.exists():
        return FileResponse(str(live_path))
    return {"message": "Live tracking page not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
