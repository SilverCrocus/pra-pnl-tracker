"""Pipeline runner service - executes the daily NBA PRA pipeline."""
import subprocess
import logging
from pathlib import Path
from datetime import datetime

from app.services.db_sync import sync_all_bets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_command(cmd: list, description: str) -> bool:
    """
    Run a shell command and log the result.

    Returns True if successful, False otherwise.
    """
    logger.info(f"Running: {description}")
    logger.info(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            logger.info(f"SUCCESS: {description}")
            if result.stdout:
                logger.debug(result.stdout)
            return True
        else:
            logger.error(f"FAILED: {description}")
            logger.error(f"Return code: {result.returncode}")
            logger.error(f"Stderr: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"TIMEOUT: {description} exceeded 10 minutes")
        return False
    except Exception as e:
        logger.error(f"ERROR: {description} - {str(e)}")
        return False


def run_daily_pipeline():
    """
    Run the full daily pipeline:
    1. uv run nba-pra pipeline --shadow-mode
    2. uv run nba-pra goldilocks-v2
    3. uv run nba-pra v2-track
    4. Sync to database
    """
    start_time = datetime.now()
    logger.info(f"Starting daily pipeline at {start_time}")

    results = {
        "pipeline": False,
        "goldilocks": False,
        "v2_track": False,
        "db_sync": False,
    }

    # Step 1: Run pipeline --shadow-mode
    results["pipeline"] = run_command(
        ["uv", "run", "nba-pra", "pipeline", "--shadow-mode"],
        "NBA PRA Pipeline (shadow mode)"
    )

    if not results["pipeline"]:
        logger.warning("Pipeline failed, continuing with existing data...")

    # Step 2: Run goldilocks-v2
    results["goldilocks"] = run_command(
        ["uv", "run", "nba-pra", "goldilocks-v2"],
        "Goldilocks V2 filter"
    )

    if not results["goldilocks"]:
        logger.warning("Goldilocks filter failed, continuing...")

    # Step 3: Run v2-track
    results["v2_track"] = run_command(
        ["uv", "run", "nba-pra", "v2-track"],
        "V2 result tracker"
    )

    if not results["v2_track"]:
        logger.warning("V2 tracker failed, continuing...")

    # Step 4: Sync to database
    try:
        logger.info("Syncing bets to database...")
        data_dir = PROJECT_ROOT / "data"
        sync_all_bets(data_dir)
        results["db_sync"] = True
        logger.info("Database sync complete")
    except Exception as e:
        logger.error(f"Database sync failed: {str(e)}")
        results["db_sync"] = False

    # Summary
    end_time = datetime.now()
    duration = end_time - start_time

    logger.info("=" * 50)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 50)
    for step, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"  {status} {step}")
    logger.info(f"Duration: {duration}")
    logger.info("=" * 50)

    return results


if __name__ == "__main__":
    run_daily_pipeline()
