from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from databases import Database
from sqlalchemy import select
from dotenv import load_dotenv
from supabase import create_client, Client
import logging
import os
from database import urls
from database_manager import DatabaseManager

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
BASE_URL = os.getenv("BASE_URL")

for var, value in [("DATABASE_URL", DATABASE_URL), ("SUPABASE_URL", SUPABASE_URL),
                   ("SUPABASE_API_KEY", SUPABASE_API_KEY), ("BASE_URL", BASE_URL)]:
    if not value:
        logger.error(f"{var} environment variable is not set.")
        raise ValueError(f"{var} environment variable is not set.")

logger.info(f"Using BASE_URL: {BASE_URL}")

# Database and Supabase clients
database = Database(DATABASE_URL, min_size=1, max_size=3, ssl=True, command_timeout=30.0)
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)
dbm = DatabaseManager(database, urls, supabase_client)

# FastAPI app setup
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model
class URLRequest(BaseModel):
    original_url: str
    custom_short: str | None = None

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred."},
    )

# Dependency to get database manager
async def get_dbm():
    yield dbm

# Routes
@app.get("/")
async def serve_homepage():
    return FileResponse("static/index.html")

@app.post("/shorten")
async def shorten_url(request: URLRequest):
    try:
        logger.info(f"Request from shorten: {request.original_url[:30]}...")
        short_id = await dbm.add_url(request.original_url, request.custom_short)
        short_url = f"{BASE_URL}/{short_id}"

        query = select(urls).where(urls.c.short_url == short_id)
        result = await database.fetch_one(query)

        if not result:
            return JSONResponse(status_code=500, content={"error": "Failed to retrieve URL info"})

        return {
            "original_url": request.original_url,
            "short_url": short_url,
            "qr_code_url": result["qr_code"]
        }
    except Exception as e:
        logger.error(f"shorten_url error: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Failed to shorten URL"})

@app.get("/{short_url}")
async def redirect_to_long_url(short_url: str):
    try:
        result = await dbm.get_url(short_url)
        if result:
            return RedirectResponse(url=result["long_url"])

        return JSONResponse(status_code=404, content={"error": "Short URL not found"})
    except Exception as e:
        logger.error(f"Redirect error for {short_url}: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "Redirect failed"})

@app.get("/health")
async def health_check():
    status = {"status": "checking", "database": "unknown"}
    try:
        temp_db = Database(DATABASE_URL, ssl=True)
        await temp_db.connect()
        await temp_db.fetch_one("SELECT 1")
        await temp_db.disconnect()
        status.update(status="healthy", database="connected")
        return status
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        status.update(status="unhealthy", database="error", error=str(e))
        return JSONResponse(status_code=503, content=status)

# Startup event
@app.on_event("startup")
async def startup():
    try:
        logger.info("Connecting to database...")
        await database.connect()
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Startup DB connection failed: {str(e)}")

# No per-request middleware to connect/disconnect — let FastAPI events manage it
@app.on_event("shutdown")
async def shutdown():
    if database.is_connected:
        logger.info("Disconnecting database...")
        await database.disconnect()
        logger.info("Database disconnected")