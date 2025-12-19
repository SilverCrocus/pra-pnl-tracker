"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api import routes
from app.models.database import init_db
from app.services.db_sync import sync_all_bets

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
    """Initialize database and sync bets on startup."""
    init_db()
    # Sync bets from CSV files
    data_dir = Path(__file__).parent.parent / "data"
    if data_dir.exists():
        sync_all_bets(data_dir)


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


@app.get("/bets")
async def bets_page():
    """Serve the today's bets HTML."""
    bets_path = static_dir / "bets.html"
    if bets_path.exists():
        return FileResponse(str(bets_path))
    return {"message": "Bets page not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
