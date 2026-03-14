import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from .ingest.pipeline import IngestResult, run_ingest

logger = logging.getLogger("selfpace")
logging.basicConfig(level=logging.INFO)

DATA_DIR = Path("/data")
IMPORTS_DIR = DATA_DIR / "imports"
RAW_DIR = DATA_DIR / "raw"
PARQUET_DIR = DATA_DIR / "parquet"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run ingest on startup if imports exist
    for d in (IMPORTS_DIR, RAW_DIR, PARQUET_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if any(IMPORTS_DIR.iterdir()):
        logger.info("Running startup ingest...")
        result = run_ingest(IMPORTS_DIR, RAW_DIR, PARQUET_DIR)
        logger.info("Startup ingest: %s", result)
    yield


app = FastAPI(title="SelfPace", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"app": "selfpace", "version": "0.1.0"}


@app.post("/ingest")
def ingest():
    result: IngestResult = run_ingest(IMPORTS_DIR, RAW_DIR, PARQUET_DIR)
    return {
        "processed": result.processed,
        "skipped": result.skipped,
        "errors": result.errors,
    }
