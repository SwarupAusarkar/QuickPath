from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from databases import Database
from sqlalchemy import select
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import urls
from database_manager import DatabaseManager
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import asyncio

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get environment variables with better error handling
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set.")
    raise ValueError("DATABASE_URL environment variable is not set.")

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    logger.error("SUPABASE_URL environment variable is not set.")
    raise ValueError("SUPABASE_URL environment variable is not set.")

SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
if not SUPABASE_API_KEY:
    logger.error("SUPABASE_API_KEY environment variable is not set.")
    raise ValueError("SUPABASE_API_KEY environment variable is not set.")

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    logger.error("BASE_URL environment variable is not set.")
    raise ValueError("BASE_URL environment variable is not set.")

logger.info(f"Using BASE_URL: {BASE_URL}")

# Initialize database with better connection options
database = Database(
    DATABASE_URL,
    min_size=1,
    max_size=3,
    ssl=True,
    echo=True,
    pool_recycle=300,  # Recycle connections after 5 minutes
    command_timeout=30.0  # 30 second timeout for commands
)

# Initialize Supabase client
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)

# Create database manager
dbm = DatabaseManager(database, urls, supabase_client)

# FastAPI app setup with custom exception handling
app = FastAPI()

# Add exception handler for database errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if "Event loop is closed" in str(exc) or "another operation is in progress" in str(exc):
        # Handle event loop issues specially
        logger.error(f"Event loop or connection error: {str(exc)}")
        return JSONResponse(
            status_code=503,
            content={"error": "Database connection issue, please try again."},
        )
    # General exception handling
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred."},
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for URL shortening request
class URLRequest(BaseModel):
    original_url: str
    custom_short: Optional[str] = None

# Safe database connection context manager
@asynccontextmanager
async def get_connection():
    try:
        if not database.is_connected:
            await database.connect()
        yield database
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection failed")
    # Don't disconnect here in serverless environment

# Database manager dependency with safer connection handling
async def get_dbm():
    try:
        if not database.is_connected:
            await database.connect()
        yield dbm
    except Exception as e:
        logger.error(f"Database manager error: {str(e)}")
        raise HTTPException(status_code=503, detail="Database service unavailable")

# Route to serve homepage
@app.get("/")
async def serve_homepage():
    return FileResponse("static/index.html")

# Route to shorten URLs with better error handling
@app.post("/shorten")
async def shorten_url(request: URLRequest):
    try:
        logger.info(f"Received request to shorten: {request.original_url[:30]}...")
        
        # Connect to database if needed
        if not database.is_connected:
            await database.connect()
            
        # Add URL
        short_id = await dbm.add_url(request.original_url, request.custom_short)
        short_url = f"{BASE_URL}/{short_id}"
        
        # Fetch the complete record
        query = select(urls).where(urls.c.short_url == short_id)
        result = await database.fetch_one(query)
        
        if not result:
            logger.error("Failed to retrieve URL information after shortening")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to retrieve URL information"}
            )
            
        return {
            "original_url": request.original_url,
            "short_url": short_url,
            "qr_code_url": result["qr_code"]
        }
    except HTTPException as e:
        # Pass through HTTP exceptions
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except Exception as e:
        logger.error(f"Error in shorten_url: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to shorten URL. Please try again."}
        )

# Route to redirect short URLs with better error handling
@app.get("/{short_url}")
async def redirect_to_long_url(short_url: str):
    try:
        # Connect to database if needed
        if not database.is_connected:
            await database.connect()
            
        # Get URL
        result = await dbm.get_url(short_url) 
        if result:
            long_url = result["long_url"]
            return RedirectResponse(url=long_url)
        
        return JSONResponse(
            status_code=404,
            content={"error": "Short URL not found"}
        )
    except Exception as e:
        logger.error(f"Error redirecting {short_url}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Error processing redirect"}
        )

# Health check endpoint with more detailed diagnostics
@app.get("/health")
async def health_check():
    status = {"status": "checking", "database": "unknown"}
    try:
        # Try a new connection for health check
        async with Database(DATABASE_URL, force_rollback=True) as db:
            await db.fetch_one("SELECT 1")
            status["database"] = "connected"
            status["status"] = "healthy"
        return status
    except Exception as e:
        status["database"] = "error"
        status["status"] = "unhealthy"
        status["error"] = str(e)
        return JSONResponse(status_code=503, content=status)

# Add startup event to connect to database
@app.on_event("startup")
async def startup():
    try:
        logger.info("Connecting to database...")
        await database.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database on startup: {str(e)}")
        # Don't raise exception here to allow the app to start even if DB is not available