from typing import Optional
from databases import Database
from sqlalchemy import select
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import urls
from database_manager import DatabaseManager
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
BASE_URL = os.getenv("BASE_URL")

logger.info(f"DATABASE_URL configured: {bool(DATABASE_URL)}")
logger.info(f"SUPABASE_URL configured: {bool(SUPABASE_URL)}")
logger.info(f"BASE_URL configured: {bool(BASE_URL)}")

import socket

# Monkey-patch getaddrinfo to force IPv4
original_getaddrinfo = socket.getaddrinfo

def force_ipv4_getaddrinfo(*args, **kwargs):
    return original_getaddrinfo(
        *args, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, flags=0
    )

socket.getaddrinfo = force_ipv4_getaddrinfo

# Initialize database
database = Database(DATABASE_URL)

# Initialize supabase client
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)

# Create database manager
dbm = DatabaseManager(database, urls, supabase_client)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    original_url: str
    custom_short: Optional[str] = None

async def get_database():
    try:
        if not database.is_connected:
            await database.connect()
        yield database
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise e

# Database manager dependency
async def get_dbm():
    if not database.is_connected:
        await database.connect()
    yield dbm

# Route to serve homepage
@app.get("/")
async def serve_homepage():
    return FileResponse("static/index.html")

# Route to shorten URLs
@app.post("/shorten")
async def shorten_url(
    request: URLRequest, 
    db: Database = Depends(get_database),
    db_manager: DatabaseManager = Depends(get_dbm)
):
    try:
        logger.info(f"Received request to shorten: {request.original_url[:30]}...")
        
        short_id = await db_manager.add_url(request.original_url, request.custom_short)
        short_url = f"{BASE_URL}/{short_id}"

        # Fetch the complete record
        query = select(urls).where(urls.c.short_url == short_id)
        result = await db.fetch_one(query)
        
        if not result:
            return {"error": "Failed to retrieve URL information"}
            
        return {
            "original_url": request.original_url,
            "short_url": short_url,
            "qr_code_url": result["qr_code"]
        }
    except Exception as e:
        logger.error(f"Error in shorten_url: {str(e)}", exc_info=True)
        return {"error": str(e)}
    
@app.get("/{short_url}")
async def redirect_to_long_url(
    short_url: str, 
    db_manager: DatabaseManager = Depends(get_dbm)
):
    try:
        result = await db_manager.get_url(short_url) 
        if result:
            long_url = result["long_url"]
            return RedirectResponse(url=long_url)
        return {"error": "Short URL not found"}
    except Exception as e:
        return {"error": str(e)}

# Add a health check endpoint
@app.get("/health")
async def health_check(db: Database = Depends(get_database)):
    try:
        await db.fetch_one("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503