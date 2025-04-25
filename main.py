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

# Create a database connection factory to ensure fresh connections for each request
def get_database():
    db = Database(DATABASE_URL, min_size=1, max_size=3, ssl=True, command_timeout=30.0)
    return db

# Supabase client - can be reused
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)

# Create context manager for database connections
@asynccontextmanager
async def get_db_context():
    db = get_database()
    try:
        await db.connect()
        logger.info("Database connected")
        yield db
    finally:
        await db.disconnect()
        logger.info("Database disconnected")

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

# Routes
@app.get("/")
async def serve_homepage():
    return FileResponse("static/index.html")

@app.post("/shorten")
async def shorten_url(request: URLRequest):
    try:
        logger.info(f"Request from shorten: {request.original_url[:30]}...")
        
        # Use context manager for database connection
        async with get_db_context() as db:
            # Create a new database manager for this request
            db_manager = DatabaseManager(db, urls, supabase_client)
            
            short_id = await db_manager.add_url(request.original_url, request.custom_short)
            short_url = f"{BASE_URL}/{short_id}"

            query = select(urls).where(urls.c.short_url == short_id)
            result = await db.fetch_one(query)

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
        # Use context manager for database connection
        async with get_db_context() as db:
            # Create a new database manager for this request
            db_manager = DatabaseManager(db, urls, supabase_client)
            
            result = await db_manager.get_url(short_url)
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
        # Create a fresh database connection for health check
        async with get_db_context() as db:
            await db.fetch_one("SELECT 1")
            status.update(status="healthy", database="connected")
        return status
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        status.update(status="unhealthy", database="error", error=str(e))
        return JSONResponse(status_code=503, content=status)